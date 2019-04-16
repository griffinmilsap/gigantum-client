// vendor
import { graphql } from 'react-relay';
// environment
import { fetchQuery } from 'JS/createRelayEnvironment';

const DatasetVisibilityLookupQuery = graphql`
  query DatasetVisibilityLookupQuery($ids: [String]!){
    datasetList{
      localById(ids: $ids){
        visibility
      }
    }
  }
`;

const Visibility = {
  constructor() {
    this.query = this.query;
  },

  query: (ids) => {
    const variables = { ids };
    return new Promise((resolve, reject) => {
      const fetchData = () => {
        fetchQuery(
          DatasetVisibilityLookupQuery(),
          variables,
        ).then((response) => {
          resolve(response);
        }).catch((error) => {
          console.log(error);
          reject(error);
        });
      };

      fetchData();
    });
  },
};

export default Visibility;
