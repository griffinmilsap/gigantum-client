// vendor
import React, { Component } from 'react';
import { connect } from 'react-redux';
import { boundMethod } from 'autobind-decorator';
import isEqual from 'react-fast-compare';
// mutations
import FileBrowser from 'Components/shared/fileBrowser/FileBrowser';

class SectionBrowser extends Component {
  state = {
    hasFiles: false,
    moreLoading: false,
    dataset: {
      isProcessing: false,
    },
  }

  /*
    handle state and addd listeners when component mounts
  */
  componentDidMount() {
    const { props, state } = this;

    props.loadStatus(state.moreLoading);

    if (props[props.section].allFiles
      && props[props.section].allFiles.pageInfo.hasNextPage) {
      this._loadMore(); // routes query only loads 2, call loadMore
    } else {
      this.setState({ moreLoading: false });
    }
  }


  static getDerivedStateFromProps(props, state) {
    let hasFiles = props[props.section]
      && (props[props.section].allFiles.edges.length > 0);
    hasFiles = (props.section === 'output') ? (props[props.section]
      && (props[props.section].allFiles.edges.length > 1)) : hasFiles;

    return {
      ...state,
      hasFiles,
    };
  }

  shouldComponentUpdate(nextProps, nextState) {
    return !isEqual(this.props, nextProps);
  }

  /*
    loads more if branches are switched
  */
  componentDidUpdate(prevProps, prevState) {
    const { props, state } = this;

    props.loadStatus(state.moreLoading);

    if (!state.moreLoading
      && props[props.section].allFiles
      && props[props.section].allFiles.pageInfo.hasNextPage) {
      this._loadMore();
    }
  }


  /*
    @param {}
    triggers relay pagination function loadMore
    increments by 100
    logs callback
  */
  @boundMethod
  _loadMore() {
    const { props } = this;
    const self = this;
    this.setState({ moreLoading: true });

    props.relay.loadMore(
      100, // Fetch the next 100 feed items
      (response, error) => {
        if (error) {
          console.error(error);
        }
        if (props[props.section].allFiles
         && props[props.section].allFiles.pageInfo.hasNextPage) {
          self._loadMore();
        } else {
          self.setState({ moreLoading: false });
        }
      },
    );
  }

  render() {
    const { props } = this;
    if (props[props.section] && props[props.section].allFiles) {
      const capitalSection = props.section[0].toUpperCase() + props.section.slice(1);
      let files = props[props.section].allFiles;

      if (props[props.section].allFiles.edges.length === 0) {
        files = {
          edges: [],
          pageInfo: props[props.section].allFiles.pageInfo,
        };
      }

      return (
        <FileBrowser
          ref={inst => inst}
          section={props.section}
          selectedFiles={props.selectedFiles}
          clearSelectedFiles={props.clearSelectedFiles}
          files={files}
          isProcessing={props.isProcessing}
          parentId={props.sectionId}
          connection={`${capitalSection}Browser_allFiles`}
          isLocked={props.isLocked}
          containerStatus={props.containerStatus}
          loadMore={this._loadMore}
          lockFileBrowser={props.lockFileBrowser}
          {...props}
        />
      );
    }
    return (<div>No Files Found</div>);
  }
}


const mapStateToProps = state => ({
  isProcessing: state.dataset.isProcessing,
});

const mapDispatchToProps = () => ({});


export default connect(mapStateToProps, mapDispatchToProps)(SectionBrowser);
