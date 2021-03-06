import {
  commitMutation,
  graphql,
} from 'react-relay';
import RelayRuntime from 'relay-runtime';
import uuidv4 from 'uuid/v4';
// environment
import environment from 'JS/createRelayEnvironment';
// redux
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
  mutation MoveDatasetFileMutation($input: MoveDatasetFileInput!){
    moveDatasetFile(input: $input){
      updatedEdges{
        node{
            id
            isDir
            modifiedAt
            isLocal
            key
            size
          }
          cursor
      }
      clientMutationId
    }
  }
`;

function sharedDeleteUpdater(store, datasetID, removeIds, connectionKey) {
  const datasetProxy = store.get(datasetID);
  if (datasetProxy) {
    removeIds.forEach((deletedID) => {
      const conn = RelayRuntime.ConnectionHandler.getConnection(
        datasetProxy,
        connectionKey,
      );

      if (conn) {
        RelayRuntime.ConnectionHandler.deleteNode(
          conn,
          deletedID,
        );
        store.delete(deletedID);
      }
    });
  }
}


export default function MoveDatasetFileMutation(
  connectionKey,
  datasetOwner,
  datasetName,
  datasetId,
  edge,
  srcPath,
  dstPath,
  section,
  removeIds,
  callback,
) {
  const variables = {
    input: {
      datasetOwner,
      datasetName,
      srcPath,
      dstPath,
      clientMutationId: uuidv4(),
    },
  };

  const configs = [{
    type: 'RANGE_ADD',
    parentID: datasetId,
    connectionInfo: [{
      key: connectionKey,
      rangeBehavior: 'append',
    }],
    edgeName: 'newDatasetFileEdge',
  }];

  if (removeIds && removeIds.length) {
    removeIds.forEach((id) => {
      configs.unshift({
        type: 'NODE_DELETE',
        deletedIDFieldName: id,
      });
    });
  }


  commitMutation(
    environment,
    {
      mutation,
      variables,
      onCompleted: (response, error) => {
        if (error) {
          console.log(error);
          setErrorMessage(datasetOwner, datasetName, `ERROR: Could not Move dataset file ${srcPath}`, error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),
      optimisticUpdater: (store) => {
        const datasetProxy = store.get(datasetId);

        if (datasetProxy && (edge.node !== null)) {
          const conn = RelayRuntime.ConnectionHandler.getConnection(
            datasetProxy,
            connectionKey,
          );

          const node = store.get(edge.node.id);
          node.setValue(edge.node.id, 'id');
          node.setValue(edge.node.isDir, 'isDir');
          node.setValue(dstPath, 'key');
          node.setValue(edge.node.modifiedAt, 'modifiedAt');
          node.setValue(edge.node.size, 'size');
          const newEdge = RelayRuntime.ConnectionHandler.createEdge(
            store,
            conn,
            node,
            'newDatasetFileEdge',
          );
          RelayRuntime.ConnectionHandler.insertEdgeAfter(
            conn,
            newEdge,
            edge.cursor,
          );
        }
      },
      updater: (store, response) => {
        sharedDeleteUpdater(store, datasetId, removeIds, connectionKey);
        if (response && response.moveDatasetFile && response.moveDatasetFile.updatedEdges) {
          response.moveDatasetFile.updatedEdges.forEach((datasetEdge) => {
            const datasetProxy = store.get(datasetId);

            if (datasetProxy && (datasetEdge.node !== null)) {
              const conn = RelayRuntime.ConnectionHandler.getConnection(
                datasetProxy,
                connectionKey,
              );

              const node = store.get(datasetEdge.node.id) ? store.get(datasetEdge.node.id) : store.create(datasetEdge.node.id, 'DatasetFile');

              node.setValue(datasetEdge.node.id, 'id');
              node.setValue(datasetEdge.node.isDir, 'isDir');
              node.setValue(datasetEdge.node.key, 'key');
              node.setValue(datasetEdge.node.modifiedAt, 'modifiedAt');
              node.setValue(datasetEdge.node.size, 'size');
              const newEdge = RelayRuntime.ConnectionHandler.createEdge(
                store,
                conn,
                node,
                'newDatasetFileEdge',
              );
              RelayRuntime.ConnectionHandler.insertEdgeAfter(
                conn,
                newEdge,
                datasetEdge.cursor,
              );
            }
          });
        }
      },

    },
  );
}
