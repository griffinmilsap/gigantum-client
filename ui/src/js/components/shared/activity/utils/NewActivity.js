// vendor
import { graphql } from 'react-relay';
// environment
import { fetchQuery } from 'JS/createRelayEnvironment';


const labbbokActivityFetchQuery = graphql`
 query NewActivityQuery($name: String!, $owner: String!, $first: Int!){
   labbook(name: $name, owner: $owner){
     activityRecords(first: $first){
       edges{
         node{
           id
           commit
         }
       }
     }
   }
 }`;


const datasetActivityFetchQuery = graphql`
  query NewActivityDatasetQuery($name: String!, $owner: String!, $first: Int!){
    dataset(name: $name, owner: $owner){
      activityRecords(first: $first){
        edges{
          node{
            id
            commit
          }
        }
      }
    }
  }`;

const NewActivity = {
  getNewActivity: (name, owner, sectionType) => {
    const variables = {
      name,
      owner,
      first: 1,
    };
    const query = (sectionType === 'labbook')
      ? labbbokActivityFetchQuery()
      : datasetActivityFetchQuery();

    return new Promise((resolve, reject) => {
      fetchQuery(query, variables).then((response, error) => {
        resolve(response);
      }).catch((error) => {
        console.log(error);
        reject(error);
      });
    });
  },
};

export default NewActivity;
