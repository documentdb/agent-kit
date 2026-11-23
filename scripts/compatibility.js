const crypto = require('node:crypto');
const marker = 'LEAN_COMPATIBILITY_RESULT=';

class UnsupportedBehavior extends Error {}

function requireBehavior(condition, detail) {
  if (!condition) throw new UnsupportedBehavior(detail);
}

const probes = {
  crud: {
    scope: 'Insert, filtered read, atomic $set/$inc, and delete on a small collection.',
    async run(database) {
      const collection = database.getCollection('crud');
      await collection.insertOne({ _id: 'record', state: 'open', visits: 0 });
      requireBehavior((await collection.findOne({ state: 'open' }))?._id === 'record', 'Filtered read failed.');
      await collection.updateOne({ _id: 'record' }, { $set: { state: 'done' }, $inc: { visits: 1 } });
      const updated = await collection.findOne({ _id: 'record' });
      requireBehavior(updated.state === 'done' && updated.visits === 1, 'Atomic update did not persist.');
      await collection.deleteOne({ _id: 'record' });
      requireBehavior(await collection.findOne({ _id: 'record' }) === null, 'Delete did not persist.');
    },
  },
  'unique-index': {
    scope: 'A unique scalar index rejects a duplicate key and preserves one record.',
    async run(database) {
      const collection = database.getCollection('unique_keys');
      await collection.createIndex({ voteKey: 1 }, { unique: true, name: 'one_vote' });
      await collection.insertOne({ voteKey: 'idea:member' });
      let rejected = false;
      try {
        await collection.insertOne({ voteKey: 'idea:member' });
      } catch (error) {
        if (error.code !== 11000) throw error;
        rejected = true;
      }
      requireBehavior(rejected, 'A duplicate unique key was accepted.');
      requireBehavior(await collection.countDocuments({}) === 1, 'Duplicate rejection changed the record count.');
    },
  },
  'compound-index': {
    scope: 'Compound index creation plus equality filtering and descending sort; not planner index-use proof.',
    async run(database) {
      const collection = database.getCollection('compound_keys');
      await collection.createIndex({ tenant: 1, score: -1 }, { name: 'tenant_score' });
      await collection.insertMany([
        { tenant: 'sample', score: 1 }, { tenant: 'sample', score: 3 }, { tenant: 'other', score: 5 },
      ]);
      const index = (await collection.getIndexes()).find(item => item.name === 'tenant_score');
      requireBehavior(index?.key.tenant === 1 && index?.key.score === -1, 'Compound index definition differs.');
      const rows = await collection.find({ tenant: 'sample' }).sort({ score: -1 }).toArray();
      requireBehavior(rows.length === 2 && rows[0].score === 3 && rows[1].score === 1, 'Filter/sort results differ.');
    },
  },
  'ttl-index-definition': {
    scope: 'TTL index creation and expireAfterSeconds metadata only; background deletion is not tested.',
    async run(database) {
      const collection = database.getCollection('ttl_keys');
      await collection.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0, name: 'expires' });
      const index = (await collection.getIndexes()).find(item => item.name === 'expires');
      requireBehavior(Number(index?.expireAfterSeconds) === 0, 'TTL definition was not retained.');
    },
  },
  'case-insensitive-collation': {
    scope: 'Case-insensitive collation on both index creation and a find query.',
    async run(database) {
      const collection = database.getCollection('collation_keys');
      const collation = { locale: 'en', strength: 2 };
      await collection.createIndex({ username: 1 }, { collation, name: 'case_comparison' });
      await collection.insertOne({ username: 'Alpha' });
      const rows = await collection.find({ username: 'alpha' }).collation(collation).toArray();
      requireBehavior(rows.length === 1, 'Case-insensitive comparison did not match.');
    },
  },
  'multi-document-transactions': {
    scope: 'Abort and commit across two collections using a MongoDB session.',
    async run(database, admin) {
      await database.createCollection('transaction_a');
      await database.createCollection('transaction_b');
      const session = admin.getMongo().startSession({ causalConsistency: false });
      try {
        const scoped = session.getDatabase(database.getName());
        session.startTransaction();
        await scoped.transaction_a.insertOne({ _id: 'aborted' });
        await scoped.transaction_b.insertOne({ _id: 'aborted' });
        await session.abortTransaction();
        requireBehavior(
          await database.transaction_a.countDocuments({}) === 0 && await database.transaction_b.countDocuments({}) === 0,
          'Aborted writes remained visible.',
        );
        session.startTransaction();
        await scoped.transaction_a.insertOne({ _id: 'committed' });
        await scoped.transaction_b.insertOne({ _id: 'committed' });
        await session.commitTransaction();
        requireBehavior(
          await database.transaction_a.countDocuments({}) === 1 && await database.transaction_b.countDocuments({}) === 1,
          'Committed writes were not visible in both collections.',
        );
      } finally {
        try { await session.abortTransaction(); } catch {}
        try { await session.endSession(); } catch {}
      }
    },
  },
};

(async () => {
  const features = [...new Set((process.env.LEAN_FEATURES || '').split(',').map(value => value.trim()).filter(Boolean))];
  const result = {
    observedAt: new Date().toISOString(), ready: false,
    probeDatabase: null, probeDatabaseRemoved: null, features: [],
  };
  let database;
  try {
    const username = encodeURIComponent(process.env.USERNAME || '');
    const password = encodeURIComponent(process.env.PASSWORD || '');
    const uri = `mongodb://${username}:${password}@127.0.0.1:10260/admin?authSource=admin&authMechanism=SCRAM-SHA-256&tls=true&tlsAllowInvalidCertificates=true&directConnection=true&retryWrites=false&serverSelectionTimeoutMS=5000&socketTimeoutMS=10000`;
    const admin = await connect(uri);
    requireBehavior((await admin.runCommand({ ping: 1 })).ok === 1, 'Authenticated ping failed.');
    result.ready = true;
    if (features.some(id => Object.prototype.hasOwnProperty.call(probes, id))) {
      result.probeDatabase = `lean_probe_${crypto.randomBytes(16).toString('hex')}`;
      database = admin.getSiblingDB(result.probeDatabase);
    }
    for (const id of features) {
      if (!Object.prototype.hasOwnProperty.call(probes, id)) {
        result.features.push({ id, status: 'unverified', detail: 'No built-in probe. Add an app-specific check for this requirement.' });
        continue;
      }
      const probe = probes[id];
      try {
        await probe.run(database, admin);
        result.features.push({ id, status: 'supported', scope: probe.scope });
      } catch (error) {
        const unsupported = error instanceof UnsupportedBehavior || [59, 115].includes(error.code)
          || (id === 'multi-document-transactions' && error.code === 20);
        result.features.push({
          id, status: unsupported ? 'unsupported' : 'unverified', scope: probe.scope,
          errorCode: error.code ?? null,
          detail: error instanceof UnsupportedBehavior ? error.message
            : unsupported ? 'The selected image explicitly rejected this capability.'
              : 'Probe execution failed; this is not evidence that the capability is unsupported.',
        });
      }
    }
  } catch (error) {
    result.error = { errorCode: error.code ?? null, detail: 'Authenticated database readiness/probe setup failed.' };
    for (const id of features) {
      if (!result.features.some(feature => feature.id === id)) {
        result.features.push({ id, status: 'unverified', detail: 'Readiness/setup failed before this requirement could be checked.' });
      }
    }
  } finally {
    if (database) {
      try {
        result.probeDatabaseRemoved = (await database.dropDatabase()).ok === 1;
      } catch {
        result.probeDatabaseRemoved = false;
      }
    }
  }
  const unverified = !result.ready || result.probeDatabaseRemoved === false
    || result.features.some(feature => feature.status === 'unverified');
  const unsupported = result.features.some(feature => feature.status === 'unsupported');
  print(marker + JSON.stringify(result));
  quit(unverified ? 2 : unsupported ? 1 : 0);
})().catch(() => {
  print(marker + JSON.stringify({ ready: false, error: { detail: 'Probe execution failed before evidence was collected.' }, features: [] }));
  quit(2);
});
