// vendor
import React, { Component } from 'react';
import { QueryRenderer, graphql } from 'react-relay';
// environment
import environment from 'JS/createRelayEnvironment';
// store
import { setUpdateAll } from 'JS/redux/actions/routes';
// components
import Loader from 'Components/common/Loader';
import Labbook from './Labbook';

// labbook query with notes fragment
export const labbookQuery = graphql`
  query LabbookQueryContainerQuery($name: String!, $owner: String!, $first: Int!, $cursor: String, $skipPackages: Boolean!, $environmentSkip: Boolean!, $overviewSkip: Boolean!, $activitySkip: Boolean!, $codeSkip: Boolean!, $inputSkip: Boolean!, $outputSkip: Boolean!, $labbookSkip: Boolean!){
    labbook(name: $name, owner: $owner){
      id
      description
      ...Labbook_labbook
    }
  }`;

class LabbookQueryContainer extends Component {
  componentDidMount() {
    setUpdateAll(this.props.owner, this.props.labbookName);
  }

  render() {
    const parentProps = this.props;
    return (
      <QueryRenderer
        environment={environment}
        query={labbookQuery}
        variables={
          {
            name: parentProps.labbookName,
            owner: parentProps.owner,
            first: 10,
            hasNext: false,
            skip: true,
            labbookSkip: true,
            environmentSkip: true,
            overviewSkip: true,
            activitySkip: true,
            inputSkip: true,
            outputSkip: true,
            codeSkip: true,
            skipPackages: true,
          }
        }
        render={({ error, props }) => {
          if (error) {
            console.log(error);

            return (<div>{error.message}</div>);
          } if (props) {
            if (props.errors) {
              return (<div>{props.errors[0].message}</div>);
            }

            return (
              <Labbook
                key={parentProps.labbookName}
                auth={parentProps.auth}
                labbookName={parentProps.labbookName}
                query={props.query}
                labbook={props.labbook}
                owner={parentProps.owner}
                history={parentProps.history}
                diskLow={props.diskLow}
                {...parentProps}
              />
            );
          }

          return (<Loader />);
        }
      }
      />
    );
  }
}

export default LabbookQueryContainer;
