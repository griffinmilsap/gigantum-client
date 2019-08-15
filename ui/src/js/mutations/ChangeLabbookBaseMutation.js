import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';

const mutation = graphql`
  mutation ChangeLabbookBaseMutation($input: ChangeLabbookBaseInput!, $first: Int!, $cursor: String, $skipPackages: Boolean!){
    changeLabbookBase(input: $input){
      labbook {
        environment {
          baseLatestRevision
          ...Base_environment
          ...Packages_environment
        }
      }
    }
  }
`;

let tempID = 0;

export default function ChangeLabbookBaseMutation(
  owner,
  labbookName,
  repository,
  baseId,
  revision,
  callback,
) {
  tempID++;
  const variables = {
    input: {
      owner,
      labbookName,
      repository,
      baseId,
      revision,
      clientMutationId: `${tempID}`,
    },
    skipPackages: false,
    first: 10,
    cursor: null,
  };
  commitMutation(
    environment,
    {
      mutation,
      variables,
      onCompleted: (response, error) => {
        if (error) {
          console.log(error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),

      updater: (store) => {


      },
    },
  );
}
