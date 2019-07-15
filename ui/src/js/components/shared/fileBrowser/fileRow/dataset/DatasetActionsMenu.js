// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import uuidv4 from 'uuid/v4';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// mutations
import ModifyDatasetLinkMutation from 'Mutations/ModifyDatasetLinkMutation';
// store
import store from 'JS/redux/store';
import { setErrorMessage } from 'JS/redux/actions/footer';
// assets
import './DatasetActionsMenu.scss';

export default class DatasetActionsMenu extends Component {

  state = {
    showSessionValidMessage: false,
  }

  /**
  *  @param {}
  *  unlinks a dataset
  *  @return {}
  */
  _unlinkDataset = () => {
    const labbookOwner = store.getState().routes.owner;
    const { labbookName } = store.getState().routes;
    const datasetOwner = this.props.edge.node.owner;
    const { datasetName } = this.props.edge.node;

    this.setState({ buttonState: 'loading' });

    ModifyDatasetLinkMutation(
      labbookOwner,
      labbookName,
      datasetOwner,
      datasetName,
      'unlink',
      null,
      (response, error) => {
        if (error) {
          setErrorMessage('Unable to unlink dataset', error);
        }
      },
    );
  }

  /**
  *  @param {event} evt - event from clicking delete button
  *  triggers DeleteLabbookFileMutation
  *  @return {}
  */
  _triggerDeleteMutation = (evt) => {
    const { props } = this;
    const deleteFileData = {
      filePaths: [props.edge.node.key],
      edges: [props.edge],
    };

    props.mutations.deleteLabbookFiles(deleteFileData, (reponse) => {});

    this._togglePopup(evt, false);
  }

  /**
  *  @param {Object} node - Dom object to be assigned as a ref
  *  set wrapper ref
  *  @return {}
  */
  _setWrapperRef = (node) => {
    const { props } = this;
    this[props.edge.node.id] = node;
  }

  /**
   *  @param {} node - Dom object to be assigned as a ref
   *  set wrapper ref
   *  @return {}
   */
  _downloadFile = (isLocal) => {
    const { props, state } = this;
    UserIdentity.getUserIdentity().then((response) => {
      const isSessionValid = response.data && response.data.userIdentity && response.data.userIdentity.isSessionValid;

      if (!isLocal && !state.fileDownloading && !props.parentDownloading && isSessionValid) {
        const id = uuidv4;
        this.setState({ fileDownloading: true });
        const searchChildren = (parent) => {
          if (parent.children) {
            Object.keys(parent.children).forEach((childKey) => {
              if (parent.children[childKey].edge) {
                if (!parent.children[childKey].edge.node.isDir) {
                  let key = parent.children[childKey].edge.node.key;
                  if (this.props.section !== 'data') {
                    const splitKey = key.split('/');
                    key = splitKey.slice(1, splitKey.length).join('/');
                  }
                  keyArr.push(key);
                }
                searchChildren(parent.children[childKey]);
              }
            });
          }
        };

        let { key, owner, datasetName } = props.edge.node;
        const labbookOwner = store.getState().routes.owner;
        const labbookName = store.getState().routes.labbookName;
        const splitKey = key.split('/');

        if (props.section === 'data') {
          owner = labbookOwner;
          datasetName = labbookName;
        } else {
          key = splitKey.slice(1, splitKey.length).join('/');
        }

        const keyArr = props.edge.node.isDir ? [] : [key];
        if (props.folder && !props.isParent) {
          searchChildren(props.fullEdge);
        }
        let data;

        if (props.section === 'data') {
          data = {
            owner,
            datasetName,
          };
        } else {
          data = {
            owner,
            datasetName,
            labbookName,
            labbookOwner,
          };
        }
        data.successCall = () => {
          this.setState({ fileDownloading: false });
          if (props.setFolderIsDownloading) {
            props.setFolderIsDownloading(false);
          }
        };
        data.failureCall = () => {
          this.setState({ fileDownloading: false });
          if (props.setFolderIsDownloading) {
            props.setFolderIsDownloading(true);
          }
        };

        if (props.setFolderIsDownloading) {
          props.setFolderIsDownloading(true);
        }

        if (props.isParent) {
          data.allKeys = true;
        } else {
          data.allKeys = false;
          data.keys = keyArr;
        }

        const callback = (response, error) => {
          if (error) {
            this.setState({ fileDownloading: false });
          }
        };

        props.mutations.downloadDatasetFiles(data, callback);
      } else if (!isSessionValid) {
        this.setState({ showSessionValidMessage: true });

        setTimeout(() => {
          this.setState({ showSessionValidMessage: false });
        }, 5000);
      }
    });
  }

  render() {
    const { props, state } = this;
    const { isLocal } = props;
    const downloadText = isLocal ? 'Downloaded' : 'Download';
    const isLoading = state.fileDownloading
      || ((props.parentDownloading || props.isDownloading) && !isLocal);
    // declare css
    const downloadCSS = classNames({
      'Btn Btn__FileBrowserAction DatasetActionsMenu__item': true,
      'Btn__FileBrowserAction--download': !isLocal,
      'Btn__FileBrowserAction--downloaded': isLocal,
      'Btn__FileBrowserAction--loading': isLoading,
      'Btn--first': props.section === 'input',
    });

    return (

      <div
        className="DatasetActionsMenu"
        key={`${props.edge.node.id}-action-menu}`}
        ref={this._setWrapperRef}
      >
        <button
          onClick={() => this._downloadFile(isLocal)}
          className={downloadCSS}
          disabled={isLocal || isLoading}
          type="button"
        >
          {downloadText}
        </button>
      </div>
    );
  }
}
