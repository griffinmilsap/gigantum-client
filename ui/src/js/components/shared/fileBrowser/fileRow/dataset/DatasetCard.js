// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { Link } from 'react-router-dom';
// store
import { setErrorMessage, setInfoMessage } from 'JS/redux/actions/footer';
// mutations
import ModifyDatasetLinkMutation from 'Mutations/ModifyDatasetLinkMutation';
// config
import config from 'JS/config';
// components
import DatasetBody from './DatasetBody';
import DatasetsCommits from './DatasetsCommits';
// assets
import './DatasetCard.scss';

type Props = {
  checkLocal: boolean,
  dataset: {
    name: string,
    owner: string,
    commitsBehind: Number,
    overview: {
      numFiles: Number,
      totalBytes: Number,
      localBytes: Number,
    }
  },
  formattedFiles: {
    children: Array,
  },
  isLocked: boolean,
  isLocal: boolean,
  owner: string,
  name: string,
  mutationData: Object,
  mutations: {
    downloadDatasetFiles: Function,
  },
  section: string,
}

class DatasetCard extends Component<Props> {
  state = {
    expanded: false,
    unlinkPopupVisible: false,
    unlinkPending: false,
    commitsPending: false,
    downloadPending: false,
  }

  /**
  *  @param {Obect} evt
  *  @param {Boolean} expanded
  *  toggles expanded in state
  *  @return {}
  */
  _toggleExpanded = (evt, expanded) => {
    if (evt.target.nodeName !== 'BUTTON') {
      this.setState({ expanded });
    }
  }

  /**
  *  @param {Obect} evt
  *  @param {string} action
  *  unlinks a dataset
  *  @return {}
  */
  _modifyDatasetLink = (evt, action) => {
    const {
      owner,
      name,
      dataset,
    } = this.props;
    const datasetOwner = dataset.owner;
    const datasetName = dataset.name;
    const popupReference = action === 'unlink' ? action : 'commits';
    const footerReference = action === 'unlink' ? action : 'update';
    this.setState({ [`${popupReference}Pending`]: true });
    this._togglePopup(evt, false, popupReference);

    ModifyDatasetLinkMutation(
      owner,
      name,
      datasetOwner,
      datasetName,
      action,
      null,
      (response, error) => {
        if (error) {
          this.setState({ [`${popupReference}Pending`]: false });
          setErrorMessage(owner, name, `Unable to ${action} dataset`, error);
        } else {
          setInfoMessage(owner, name, `Dataset ${datasetName} has been succesfully ${footerReference}ed`);
        }
      },
    );
  }

  /**
  *  @param {}
  *  downloads a dataset
  *  @return {}
  */
  _downloadDataset = () => {
    const {
      dataset,
      owner,
      name,
      mutations,
    } = this.props;
    const datasetOwner = dataset.owner;
    const datasetName = dataset.name;
    const data = {
      labbookOwner: owner,
      datasetName,
      labbookName: name,
      owner: datasetOwner,
      allKeys: true,
    };

    data.successCall = () => {
      this.setState({ downloadPending: false });
    };
    data.failureCall = () => {
      this.setState({ downloadPending: false });
    };
    const callback = (response, error) => {
      if (error) {
        this.setState({ downloadPending: false });
      }
    };
    this.setState({ downloadPending: true });
    mutations.downloadDatasetFiles(data, callback);
  }

  /**
  *  @param {Obect} evt
  *  @param {boolean} popupVisible - boolean value for hiding and showing popup state
  *  @param {String} popupType
  *  triggers favoirte unfavorite mutation
  *  @return {}
  */
  _togglePopup = (evt, popupVisible, popupType) => {
    if (!popupVisible) {
      evt.stopPropagation();
      /**
       only stop propagation when closing popup, other menus won't close
       on click if propagation is stopped
      */
    }
    this.setState({ [`${popupType}PopupVisible`]: popupVisible });
  }

  render() {
    const {
      checkLocal,
      dataset,
      formattedFiles,
      isLocked,
      isLocal,
      mutations,
      mutationData,
      section,
    } = this.props;
    const {
      commitsPending,
      expanded,
      downloadPending,
      unlinkPending,
      unlinkPopupVisible,
    } = this.state;
    const { commitsBehind } = dataset;
    const numFilesText = `${dataset.overview.numFiles} file${(dataset.overview.numFiles === 1)
      ? ''
      : 's'}`;
    const sizeText = config.humanFileSize(dataset.overview.totalBytes);
    const unlinkDisabled = isLocked || unlinkPending;
    const downloadDisabled = isLocked || downloadPending || isLocal;
    const onDiskBytes = dataset.overview.localBytes;
    const onDiskFormatted = config.humanFileSize(onDiskBytes);
    const toDownloadBytes = dataset.overview.totalBytes - dataset.overview.localBytes;
    const toDownloadFormatted = config.humanFileSize(toDownloadBytes);
    const downloadAllText = isLocal ? 'Downloaded' : 'Download All';
    const showCommits = (commitsBehind > 0)
      || ((commitsBehind === null) && window.navigator.onLine);
    // declare css here
    const chevronCSS = classNames({
      DatasetCard__chevron: true,
      'DatasetCard__chevron--expanded': expanded,
      'DatasetCard__chevron--collapsed': !expanded,
    });
    const unlinkPopupCSS = classNames({
      DatasetCard__popup: true,
      hidden: !unlinkPopupVisible || isLocked,
      Tooltip__message: true,
    });
    const unlinkCSS = classNames({
      'Btn Btn__FileBrowserAction Btn__FileBrowserAction--unlink': true,
      'Btn__FileBrowserAction--loading': unlinkPending,
    });
    const downloadCSS = classNames({
      'Btn Btn__FileBrowserAction': true,
      'Btn__FileBrowserAction--downloaded Tooltip-data': isLocal,
      'Btn__FileBrowserAction--download': !isLocal,
      'Btn__FileBrowserAction--loading': downloadPending,
    });
    const progressCSS = classNames({
      'flex flex--column flex-1 DatasetCard__progress': true,
      'DatasetCard__progress--downloaded': toDownloadBytes === 0,
    });

    return (
      <div className="DatasetCard Card">
        <div
          role="presentation"
          className="DatasetCard__summary flex justify--space-between"
          onClick={evt => this._toggleExpanded(evt, !expanded)}
        >
          <div className={chevronCSS} />
          <div className="DatasetCard__info flex flex-1">
            <div className="DatasetCard__icon" />
            <div className="flex flex--column justify--space-between">
              <Link
                className="DatasetCard__name"
                to={`/datasets/${dataset.owner}/${dataset.name}`}
              >
                {dataset.name}
              </Link>
              <div className="DatasetCard__owner">{`by ${dataset.owner}`}</div>
              <div className="DatasetCard__details flex justify--space-between">
                <span>{sizeText}</span>
                <span>{numFilesText}</span>
              </div>
            </div>
          </div>
          <div className={progressCSS}>
            <progress
              value={onDiskBytes}
              max={dataset.overview.totalBytes}
            />
            <div className="flex justify--space-between">
              <div className="DatasetCard__onDisk flex flex--column">
                <div className="DatasetCard__onDisk--primary">{onDiskFormatted}</div>
                <div className="DatasetCard__onDisk--secondary">on disk</div>
              </div>
              { (toDownloadBytes !== 0)
                && (
                  <div className="DatasetCard__toDownload flex flex--column">
                    <div className="DatasetCard__toDownload--primary">{toDownloadFormatted}</div>
                    <div className="DatasetCard__toDownload--secondary">to download</div>
                  </div>
                )
              }
            </div>
          </div>
          <div className="flex flex--column justify--space-between align-items--end flex-1">
            <div className="relative">
              <button
                className={unlinkCSS}
                type="button"
                onClick={(evt) => { this._togglePopup(evt, true, 'unlink'); }}
                disabled={unlinkDisabled}
              >
                Unlink Dataset
              </button>
              <div className={unlinkPopupCSS}>
                <div className="Tooltip__pointer" />
                <p className="margin-top--0">Are you sure?</p>
                <div className="flex justify--space-around">
                  <button
                    className="File__btn--round File__btn--cancel"
                    onClick={(evt) => { this._togglePopup(evt, false, 'unlink'); }}
                    type="button"
                  />
                  <button
                    className="File__btn--round File__btn--add"
                    onClick={evt => this._modifyDatasetLink(evt, 'unlink')}
                    type="button"
                  />
                </div>
              </div>
            </div>
            <button
              className={downloadCSS}
              type="button"
              data-tooltip="All files for this dataset have been downloaded"
              onClick={() => this._downloadDataset()}
              disabled={downloadDisabled}
            >
              {downloadAllText}
            </button>
          </div>
        </div>
        { expanded
          && (
            <DatasetBody
              files={formattedFiles.children}
              mutationData={mutationData}
              checkLocal={checkLocal}
              downloadPending={downloadPending}
              mutations={mutations}
              section={section}
            />
          )
        }
        { showCommits
          && (
            <DatasetsCommits
              commitsPending={commitsPending}
              commitsBehind={dataset.commitsBehind}
              isLocked={isLocked}
              modifiyDatasetLink={this._modifyDatasetLink}
            />
          )
        }
      </div>
    );
  }
}

export default DatasetCard;
