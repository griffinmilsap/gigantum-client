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
const insertSecretsEdge = (edges, mutationData, component) => {
  reactRelay.commitLocalUpdate(component.props.relay.environment, (store) => {
    const {
      filename,
    } = mutationData;
    const responseNode = edges.filter(({ node }) => node.filename === filename)[0].node;
    const { id } = responseNode;
    const node = store.get(id);
    node.setValue(responseNode.isPresent, 'isPresent');
  });
};

export default {
  insertSecretsEdge,
};
