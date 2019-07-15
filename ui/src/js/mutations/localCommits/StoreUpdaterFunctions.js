// vendor
import RelayRuntime from 'relay-runtime';

/**
 @param {Object} store
 @param {String} sectionId
 @param {String} connectionKey
 @param {Object} node
 @param {String} edgeType
 Sets a proxy using the sectiong id
 Creates a connection to the proxy
 Inserts edge via the connection
*/
const insertEdgeAfter = (store, sectionId, connectionKey, node, edgeType) => {
  const sectionProxy = store.get(sectionId);

  if (sectionProxy) {
    const conn = RelayRuntime.ConnectionHandler.getConnection(
      sectionProxy,
      connectionKey,
    );

    if (conn) {
      const newEdge = RelayRuntime.ConnectionHandler.createEdge(
        store,
        conn,
        node,
        edgeType,
      );
      RelayRuntime.ConnectionHandler.insertEdgeAfter(
        conn,
        newEdge,
      );
    }
  }
};

/**
 @param {Object} store
 @param {String} sectionId
 @param {String} connectionKey
 @param {String} nodeId
 Sets a proxy using the sectiong id
 Creates a connection to the proxy
 Deletes edge via the connection
*/
const deleteEdge = (store, sectionId, connectionKey, nodeId) => {
  const sectionProxy = store.get(sectionId);
  if (sectionProxy) {
    const conn = RelayRuntime.ConnectionHandler.getConnection(
      sectionProxy,
      connectionKey,
    );
    if (conn) {
      RelayRuntime.ConnectionHandler.deleteNode(
        sectionProxy,
        nodeId,
      );
      store.delete(nodeId);
    }
  }
};

export default {
  insertEdgeAfter,
  deleteEdge,
};
