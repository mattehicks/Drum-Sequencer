// AWS store: DynamoDB single table for users/metadata/share slugs, S3 for project JSON bodies.
//
// Items (pk / sk):
//   EMAIL#<email>  / AUTH       -> userId, pw_hash          (enforces unique email)
//   USER#<uid>     / PROFILE    -> id, email, created_at
//   USER#<uid>     / PROJ#<pid> -> id, name, share_slug?, created_at, updated_at, bytes
//   SHARE#<slug>   / SHARE      -> uid, pid
// S3: projects/<uid>/<pid>.json
import crypto from 'node:crypto';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import {
  DynamoDBDocumentClient, GetCommand, PutCommand, UpdateCommand, DeleteCommand,
  QueryCommand, TransactWriteCommand,
} from '@aws-sdk/lib-dynamodb';
import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';

const now = () => new Date().toISOString();
const newId = () => crypto.randomBytes(9).toString('base64url');
const isCondFail = (e) =>
  e?.name === 'ConditionalCheckFailedException' ||
  (e?.name === 'TransactionCanceledException' &&
    (e.CancellationReasons || []).some(r => r?.Code === 'ConditionalCheckFailed'));

export function awsStore({ table, bucket, region }) {
  const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({ region }), {
    marshallOptions: { removeUndefinedValues: true },
  });
  const s3 = new S3Client({ region });
  const key = (uid, pid) => `projects/${uid}/${pid}.json`;
  const validId = (id) => typeof id === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(id);

  async function getMeta(uid, pid) {
    if (!validId(String(pid))) return null;
    const r = await ddb.send(new GetCommand({ TableName: table, Key: { pk: `USER#${uid}`, sk: `PROJ#${pid}` } }));
    return r.Item || null;
  }
  async function getBody(uid, pid) {
    const r = await s3.send(new GetObjectCommand({ Bucket: bucket, Key: key(uid, pid) }));
    return r.Body.transformToString('utf-8');
  }
  function putBody(uid, pid, data) {
    return s3.send(new PutObjectCommand({
      Bucket: bucket, Key: key(uid, pid), Body: data, ContentType: 'application/json',
    }));
  }
  const pub = (m) => ({
    id: m.id, name: m.name, share_slug: m.share_slug || null,
    created_at: m.created_at, updated_at: m.updated_at, bytes: m.bytes,
  });

  return {
    async createUser(email, pwHash) {
      const id = crypto.randomUUID();
      const created_at = now();
      try {
        await ddb.send(new TransactWriteCommand({ TransactItems: [
          { Put: { TableName: table, Item: { pk: `EMAIL#${email}`, sk: 'AUTH', userId: id, pw_hash: pwHash },
                   ConditionExpression: 'attribute_not_exists(pk)' } },
          { Put: { TableName: table, Item: { pk: `USER#${id}`, sk: 'PROFILE', id, email, created_at } } },
        ] }));
      } catch (e) { if (isCondFail(e)) return null; throw e; }
      return { id, email, created_at };
    },

    async getAuthByEmail(email) {
      const r = await ddb.send(new GetCommand({ TableName: table, Key: { pk: `EMAIL#${email}`, sk: 'AUTH' } }));
      return r.Item ? { id: r.Item.userId, pw_hash: r.Item.pw_hash } : null;
    },

    async getUser(id) {
      if (typeof id !== 'string') return null;
      const r = await ddb.send(new GetCommand({ TableName: table, Key: { pk: `USER#${id}`, sk: 'PROFILE' } }));
      return r.Item ? { id: r.Item.id, email: r.Item.email, created_at: r.Item.created_at } : null;
    },

    async listProjects(uid) {
      const out = [];
      let ExclusiveStartKey;
      do {
        const r = await ddb.send(new QueryCommand({
          TableName: table,
          KeyConditionExpression: 'pk = :pk AND begins_with(sk, :p)',
          ExpressionAttributeValues: { ':pk': `USER#${uid}`, ':p': 'PROJ#' },
          ExclusiveStartKey,
        }));
        out.push(...r.Items.map(pub));
        ExclusiveStartKey = r.LastEvaluatedKey;
      } while (ExclusiveStartKey);
      return out.sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));
    },

    async createProject(uid, name, data) {
      const pid = newId();
      const t = now();
      await putBody(uid, pid, data);
      await ddb.send(new PutCommand({ TableName: table, Item: {
        pk: `USER#${uid}`, sk: `PROJ#${pid}`, id: pid, name, created_at: t, updated_at: t, bytes: Buffer.byteLength(data),
      } }));
      return pid;
    },

    async getProject(uid, pid) {
      const m = await getMeta(uid, pid);
      if (!m) return null;
      return { ...pub(m), data: await getBody(uid, m.id) };
    },

    async updateProject(uid, pid, name, data) {
      if (!validId(String(pid))) return false;
      try {
        await ddb.send(new UpdateCommand({
          TableName: table, Key: { pk: `USER#${uid}`, sk: `PROJ#${pid}` },
          UpdateExpression: 'SET #n = :n, updated_at = :t, bytes = :b',
          ConditionExpression: 'attribute_exists(pk)',
          ExpressionAttributeNames: { '#n': 'name' },
          ExpressionAttributeValues: { ':n': name, ':t': now(), ':b': Buffer.byteLength(data) },
        }));
      } catch (e) { if (isCondFail(e)) return false; throw e; }
      await putBody(uid, pid, data);
      return true;
    },

    async deleteProject(uid, pid) {
      if (!validId(String(pid))) return false;
      let old;
      try {
        old = (await ddb.send(new DeleteCommand({
          TableName: table, Key: { pk: `USER#${uid}`, sk: `PROJ#${pid}` },
          ConditionExpression: 'attribute_exists(pk)', ReturnValues: 'ALL_OLD',
        }))).Attributes;
      } catch (e) { if (isCondFail(e)) return false; throw e; }
      await s3.send(new DeleteObjectCommand({ Bucket: bucket, Key: key(uid, pid) }));
      if (old?.share_slug) {
        await ddb.send(new DeleteCommand({ TableName: table, Key: { pk: `SHARE#${old.share_slug}`, sk: 'SHARE' } }));
      }
      return true;
    },

    async setShare(uid, pid) {
      const m = await getMeta(uid, pid);
      if (!m) return null;
      if (m.share_slug) return m.share_slug;
      const slug = newId();
      try {
        await ddb.send(new TransactWriteCommand({ TransactItems: [
          { Put: { TableName: table, Item: { pk: `SHARE#${slug}`, sk: 'SHARE', uid, pid: m.id },
                   ConditionExpression: 'attribute_not_exists(pk)' } },
          { Update: { TableName: table, Key: { pk: `USER#${uid}`, sk: `PROJ#${m.id}` },
                      UpdateExpression: 'SET share_slug = :s',
                      ConditionExpression: 'attribute_exists(pk) AND attribute_not_exists(share_slug)',
                      ExpressionAttributeValues: { ':s': slug } } },
        ] }));
      } catch (e) {
        if (!isCondFail(e)) throw e;
        const again = await getMeta(uid, pid);   // lost a race with another share call
        return again?.share_slug || null;
      }
      return slug;
    },

    async clearShare(uid, pid) {
      if (!validId(String(pid))) return false;
      let old;
      try {
        old = (await ddb.send(new UpdateCommand({
          TableName: table, Key: { pk: `USER#${uid}`, sk: `PROJ#${pid}` },
          UpdateExpression: 'REMOVE share_slug',
          ConditionExpression: 'attribute_exists(pk)', ReturnValues: 'ALL_OLD',
        }))).Attributes;
      } catch (e) { if (isCondFail(e)) return false; throw e; }
      if (old?.share_slug) {
        await ddb.send(new DeleteCommand({ TableName: table, Key: { pk: `SHARE#${old.share_slug}`, sk: 'SHARE' } }));
      }
      return true;
    },

    async getShared(slug) {
      if (!validId(slug)) return null;
      const r = await ddb.send(new GetCommand({ TableName: table, Key: { pk: `SHARE#${slug}`, sk: 'SHARE' } }));
      if (!r.Item) return null;
      const p = await this.getProject(r.Item.uid, r.Item.pid);
      return p ? { name: p.name, updated_at: p.updated_at, data: p.data } : null;
    },
  };
}
