import {
  commitMutation,
  graphql,
} from 'react-relay';
import environment from 'JS/createRelayEnvironment';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';

const mutation = graphql`
  mutation MigrateProjectMutation($input: MigrateLabbookSchemaInput!, $first: Int, $cursor: String, $skipPackages: Boolean!, $environmentSkip: Boolean!, $overviewSkip: Boolean!, $activitySkip: Boolean!, $codeSkip: Boolean!, $inputSkip: Boolean!, $outputSkip: Boolean!, $labbookSkip: Boolean!){
    migrateLabbookSchema(input: $input){
      labbook{
        ...Labbook_labbook
      }
      clientMutationId
    }
  }
`;

let tempID = 0;

export default function MigrateProjectMutation(
  owner,
  labbookName,
  callback,
) {
  const variables = {
    input: {
      owner,
      labbookName,
      clientMutationId: tempID++,
    },
    first: 10,
    cursor: null,
    hasNext: false,
    overviewSkip: false,
    activitySkip: false,
    environmentSkip: false,
    codeSkip: false,
    inputSkip: false,
    outputSkip: false,
    labbookSkip: false,
    skipPackages: true,
  };
  commitMutation(
    environment,
    {
      mutation,
      variables,
      onCompleted: (response, error) => {
        if (error) {
          console.log(error);
          setErrorMessage(owner, labbookName, 'ERROR: Could not migrate project', error);
        }
        callback(response, error);
      },
      onError: err => console.error(err),
    },
  );
}
