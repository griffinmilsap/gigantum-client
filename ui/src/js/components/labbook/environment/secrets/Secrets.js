// vendor
import React, { Component } from 'react';
import { createPaginationContainer, graphql } from 'react-relay';
import { boundMethod } from 'autobind-decorator';
// store

// components
import SecretsCard from './SecretsCard';
// utils
import SecretsMutations from './utils/SecretsMutations';

class Secrets extends Component {
  state = {
    secretsMutations: new SecretsMutations({
      name: this.props.name,
      owner: this.props.owner,
      environmentId: this.props.environmentId,
    }),
  }

  render() {
    const { props, state } = this;
    return (
      <div className="Secrets">
        <div className="Environment__headerContainer">
          <h4>
            Sensitive Files
          </h4>
        </div>
        <div className="Secrets__sub-header">
          Sensitive Files are stored locally and copied into your Project container at runtime. They are not uploaded when syncing.
          {' '}
          <a
            href="https://docs.gigantum.com/docs/managing-secrets"
            rel="noopener noreferrer"
            target="_blank"
          >
             Learn more here.
          </a>
        </div>
        <div className="grid">
          <SecretsCard
            relay={props.relay}
            secrets={props.environment.secretsFileMapping}
            secretsMutations={state.secretsMutations}
          />
        </div>
      </div>
    );
  }
}

export default createPaginationContainer(
  Secrets,
  {
    environment: graphql`fragment Secrets_environment on Environment {
    secretsFileMapping(first: $first, after: $cursor) @connection(key: "Secrets_secretsFileMapping", filters: []){
        edges{
          node{
            id
            owner
            name
            filename
            mountPath
            isPresent
          }
          cursor
        }
        pageInfo{
          hasNextPage
          hasPreviousPage
          startCursor
          endCursor
        }
      }
    }`,
  },
  {
    direction: 'forward',
    getConnectionFromProps(props) {
      return props.environment && props.environment.secretsFileMapping;
    },
    getFragmentVariables(prevVars, first) {
      return {
        ...prevVars,
        first,
      };
    },
    getVariables(props, { count }) {
      const { length } = props.environment.secretsFileMapping.edges;
      const { labbookName, owner } = store.getState().routes;

      const lastEdge = props.environment.secretsFileMapping.edges[length - 1];
      const cursor = lastEdge ? lastEdge.cursor : null;
      const hasNext = !props.environment.secretsFileMapping.pageInfo.hasNextPage;
      const first = count;

      return {
        first,
        cursor,
        name: labbookName,
        owner,
        hasNext,
        // in most cases, for variables other than connection filters like
        // `first`, `after`, etc. you may want to use the previous values.
        // orderBy: fragmentVariables.orderBy,
      };
    },
    query: graphql`
    query SecretsPaginationQuery($name: String!, $owner: String!, $first: Int!, $cursor: String){
     labbook(name: $name, owner: $owner){
       environment{
         ...Secrets_environment
       }
     }
   }`,
  },
);
