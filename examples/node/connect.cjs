const fs = require('node:fs');
const path = require('node:path');
const { MongoClient } = require('mongodb');

async function main() {
  let options = {
    tls: true,
    tlsAllowInvalidCertificates: process.env.DOCUMENTDB_TLS_ALLOW_INVALID === 'true',
    retryWrites: false,
    serverSelectionTimeoutMS: 5000,
    socketTimeoutMS: 10000,
  };
  let uri = process.env.MONGODB_URI;
  if (!uri) {
    const filename = process.env.DOCUMENTDB_CONFIG || path.resolve(__dirname, '../../.env');
    const values = Object.fromEntries(fs.readFileSync(filename, 'utf8').split(/\r?\n/).filter(line => line && !line.startsWith('#') && line.includes('=')).map(line => {
      const at = line.indexOf('=');
      return [line.slice(0, at), line.slice(at + 1)];
    }));
    if (!values.DOCUMENTDB_USERNAME || !values.DOCUMENTDB_PASSWORD) throw new Error('Missing database credentials');
    uri = `mongodb://${process.env.DOCUMENTDB_HOST || '127.0.0.1'}:${process.env.DOCUMENTDB_PORT || values.DOCUMENTDB_PORT || '10260'}`;
    options = { ...options, auth: { username: values.DOCUMENTDB_USERNAME, password: values.DOCUMENTDB_PASSWORD }, authSource: 'admin', authMechanism: 'SCRAM-SHA-256' };
  }
  const client = new MongoClient(uri, options);
  try {
    await client.connect();
    await client.db('admin').command({ ping: 1 });
    console.log('Authenticated database ping passed.');
  } finally {
    await client.close();
  }
}

main().catch(error => {
  console.error(`Connection failed (${error.name}); check credentials, endpoint, and trusted TLS configuration.`);
  process.exitCode = 1;
});
