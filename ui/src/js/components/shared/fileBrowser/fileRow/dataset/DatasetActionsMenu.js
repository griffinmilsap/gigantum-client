// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// mutations
import ModifyDatasetLinkMutation from 'Mutations/repository/datasets/ModifyDatasetLinkMutation';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// assets
import './DatasetActionsMenu.scss';

type Props = {
  edge: {
    node: {
      datasetName: string,
      id: string,
      isDir: boolean,
      owner: string,
      key: string,
    },
  },
  folder: Object,
  fullEdge: boolean,
  isDownloading: boolean,
  isLocal: boolean,
  isParent: boolean,
  mutations: {
    deleteLabbookFiles: Function,
    downloadDatasetFiles: Function,
  },
  name: string,
  owner: string,
  section: string,
  parentDownloading: string,
  setFolderIsDownloading: Function,
};

class DatasetActionsMenu extends Component<Props> {
  state = {
    fileDownloading: false,
  }

  /**
  *  @param {}
  *  unlinks a dataset
  *  @return {}
  */
  _unlinkDataset = () => {
    const { props } = this;
    const { owner, name } = props;
    const datasetOwner = props.edge.node.owner;
    const { datasetName } = props.edge.node;

    this.setState({ buttonState: 'loading' });

    ModifyDatasetLinkMutation(
      owner,
      name,
      datasetOwner,
      datasetName,
      'unlink',
      null,
      (response, error) => {
        if (error) {
          setErrorMessage(owner, name, 'Unable to unlink dataset', error);
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
    const { edge, mutations } = this.props;
    const deleteFileData = {
      filePaths: [edge.node.key],
      edges: [edge],
    };

    mutations.deleteLabbookFiles(deleteFileData, () => {});

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
    // TODO break up this function
    const { state } = this;
    const {
      edge,
      folder,
      fullEdge,
      isParent,
      mutations,
      owner,
      name,
      parentDownloading,
      section,
      setFolderIsDownloading,
    } = this.props;

    UserIdentity.getUserIdentity().then((response) => {
      const isSessionValid = response.data && response.data.userIdentity
        && response.data.userIdentity.isSessionValid;

      if (!isLocal && !state.fileDownloading && !parentDownloading && isSessionValid) {
        this.setState({ fileDownloading: true });
        const searchChildren = (parent) => {
          if (parent.children) {
            Object.keys(parent.children).forEach((childKey) => {
              const child = parent.children[childKey];
              if (child.edge) {
                if (!child.edge.node.isDir) {
                  let { key } = child.edge.node;
                  if (section !== 'data') {
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

        let { key, datasetName } = edge.node;
        let datasetOwner = edge.node.owner;
        const splitKey = key.split('/');
        if (section === 'data') {
          datasetOwner = owner;
          datasetName = name;
        } else {
          key = splitKey.slice(1, splitKey.length).join('/');
        }

        const keyArr = edge.node.isDir ? [] : [key];
        if (folder && !isParent) {
          searchChildren(fullEdge);
        }
        let data;

        if (section === 'data') {
          data = {
            datasetOwner,
            datasetName,
          };
        } else {
          data = {
            datasetOwner,
            datasetName,
            owner,
            name,
          };
        }
        data.successCall = () => {
          this.setState({ fileDownloading: false });
          if (setFolderIsDownloading) {
            setFolderIsDownloading(false);
          }
        };
        data.failureCall = () => {
          this.setState({ fileDownloading: false });
          if (setFolderIsDownloading) {
            setFolderIsDownloading(true);
          }
        };

        if (setFolderIsDownloading) {
          setFolderIsDownloading(true);
        }

        if (isParent) {
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
        mutations.downloadDatasetFiles(data, callback);
      } else if (!isSessionValid) {
        this.setState({ showSessionValidMessage: true });

        setTimeout(() => {
          this.setState({ showSessionValidMessage: false });
        }, 5000);
      }
    });
  }

  render() {
    const { fileDownloading } = this.state;
    const {
      edge,
      isLocal,
      isDownloading,
      parentDownloading,
      section,
    } = this.props;
    const downloadText = isLocal ? 'Downloaded' : 'Download';
    const isLoading = fileDownloading
      || ((parentDownloading || isDownloading) && !isLocal);
    // declare css
    const downloadCSS = classNames({
      'Btn Btn__FileBrowserAction DatasetActionsMenu__item': true,
      'Btn__FileBrowserAction--download': !isLocal,
      'Btn__FileBrowserAction--downloaded': isLocal,
      'Btn__FileBrowserAction--loading': isLoading,
      'Btn--first': section === 'input',
    });

    return (

      <div
        className="DatasetActionsMenu"
        key={`${edge.node.id}-action-menu}`}
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

export default DatasetActionsMenu;
