// vendor
import reactRelay from 'react-relay';
// utilities
import StoreUpdaterFunctions from './StoreUpdaterFunctions';

/**
 @param {Object} edge
 @param {Object} mutationData
 @param {Object} component
 gets access to the store using commitLocalUpdate
 sets node values and writes to the relay store
 @calls {StoreUpdaterFunctions.insertEdgeAfter}
*/
const insertFileBrowserEdge = (edge, mutationData, component) => {

  reactRelay.commitLocalUpdate(component.props.relay.environment, (store) => {
    const responseNode = edge.node;
    const { id } = responseNode;
    const nodeExists = store.get(id);
    const node = nodeExists ? store.get(id) : store.create(id, 'LabbookFile');
    const responseKey = responseNode.key.startsWith('/')
      ? responseNode.key.substring(1)
      : responseNode.key;
    node.setValue(responseNode.size, 'size');
    node.setValue(false, 'isDir');
    node.setValue(responseNode.id, 'id');
    node.setValue(responseKey, 'key');
    node.setValue(responseNode.modifiedAt, 'modifiedAt');

    if (responseNode.isLocal) {
      node.setValue(responseNode.isLocal, 'isLocal');
    }

    StoreUpdaterFunctions.insertEdgeAfter(
      store,
      mutationData.parentId,
      mutationData.connection,
      node,
      'LabbookFileEdge',
    );
  });
};

export default {
  insertFileBrowserEdge,
};
