// vendor
import { graphql } from 'react-relay';
// environment
import { fetchQuery } from 'JS/createRelayEnvironment';

const fetchLabbookQuery = graphql`
  query fetchLabbookQuery($name: String!, $owner: String!, $first: Int!, $skipPackages: Boolean!, $cursor: String, $environmentSkip: Boolean!, $overviewSkip: Boolean!, $activitySkip: Boolean!, $codeSkip: Boolean!, $inputSkip: Boolean!, $outputSkip: Boolean!, $labbookSkip: Boolean!){
  labbook(name: $name, owner: $owner){
    id
    description
    ...Labbook_labbook
  }
}
`;

const FetchLabbook = {
  getLabook: (owner, labbookName) => {
    const variables = {
      owner,
      name: labbookName,
      first: 2,
      cursor: null,
      hasNext: false,
      overviewSkip: false,
      activitySkip: false,
      environmentSkip: false,
      codeSkip: false,
      inputSkip: false,
      outputSkip: false,
      skipPackages: true,
    };

    return new Promise((resolve, reject) => {
      const fetchData = function () {
        fetchQuery(fetchLabbookQuery(), variables).then((response) => {
          resolve(response.data);
        }).catch((error) => {
          reject(error);
        });
      };

      fetchData();
    });
  },
};

export default FetchLabbook;
