// vendor
import React, { Component } from 'react';
// store
import store from 'JS/redux/store';
// componenets
import RecentCard from './RecentCard';

export default class MostRecentList extends Component {
  constructor(props) {
    super(props);
    this.state = {
      sortedFiles: this.props.allFiles,
      loading: false,
      showAmount: this.props.showAmount,
      shownFiles: [],
    };
  }

  componentDidMount() {
    this.setState({ shownFiles: this.state.sortedFiles.slice(0, 3) });
  }

  static getDerivedStateFromProps(props, state) {
    return ({
      ...state,
      shownFiles: props.allFiles.slice(0, 3),
    });
  }

  render() {
    const {
      shownFiles,
    } = this.state;
    const pathArray = store.getState().routes.callbackRoute.split('/');
    let selectedPath = (pathArray.length > 4) ? pathArray[pathArray.length - 1] : 'overview';
    if (selectedPath === 'inputData' || selectedPath === 'outputData') {
      selectedPath = selectedPath.substring(0, selectedPath.length - 4);
    }
    const favoriteConnection = selectedPath === 'code' ? 'CodeFavorites_favorites'
      : selectedPath === 'input' ? 'InputFavorites_favorites'
        : 'OutputFavorites_favorites';
    const connection = selectedPath === 'code' ? 'MostRecentCode_allFiles'
      : selectedPath === 'input' ? 'MostRecentInput_allFiles'
        : 'MostRecentOutput_allFiles';

    return (
      <div className="Recent__list grid">
        {
          shownFiles.map((edge, index) => (
            <RecentCard
              key={edge.node.key}
              id={edge.node.id}
              index={index}
              labbookName={this.props.labbookName}
              parentId={this.props.edgeId}
              section={selectedPath}
              connection={connection}
              file={edge}
              owner={this.props.owner}
            />
          ))
        }
      </div>
    );
  }
}
