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

export default class DatasetCard extends Component {
  state = {
    expanded: false,
    unlinkPopupVisible: false,
    commitsPopupVisible: false,
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
    const { props } = this;
    const labbookOwner = props.owner;
    const labbookName = props.name;
    const datasetOwner = props.dataset.owner;
    const datasetName = props.dataset.name;
    const popupReference = action === 'unlink' ? action : 'commits';
    this.setState({ [`${popupReference}Pending`]: true });
    this._togglePopup(evt, false, popupReference);
    ModifyDatasetLinkMutation(
      labbookOwner,
      labbookName,
      datasetOwner,
      datasetName,
      action,
      null,
      (response, error) => {
        if (error) {
          this.setState({ [`${popupReference}Pending`]: false });
          setErrorMessage(`Unable to ${action} dataset`, error);
        } else {
          setInfoMessage(`Dataset ${datasetName} has been succesfully ${action}ed`);
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
    const { props } = this;
    const labbookOwner = props.owner;
    const labbookName = props.name;
    const { owner } = props.dataset;
    const datasetName = props.dataset.name;
    const data = {
      labbookOwner,
      datasetName,
      labbookName,
      owner,
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
    props.mutations.downloadDatasetFiles(data, callback);
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
      evt.stopPropagation(); // only stop propagation when closing popup, other menus won't close on click if propagation is stopped
    }
    this.setState({ [`${popupType}PopupVisible`]: popupVisible });
  }

  render() {
    const { props, state } = this;
    const numFilesText = `${props.dataset.overview.numFiles} file${(props.dataset.overview.numFiles === 1) ? '' : 's'}`;
    const sizeText = config.humanFileSize(props.dataset.overview.totalBytes);
    const unlinkDisabled = props.isLocked || state.unlinkPending;
    const downloadDisabled = props.isLocked || state.downloadPending || props.isLocal;
    const onDiskBytes = props.dataset.overview.localBytes;
    const onDiskFormatted = config.humanFileSize(onDiskBytes);
    const toDownloadBytes = props.dataset.overview.totalBytes - props.dataset.overview.localBytes;
    const toDownloadFormatted = config.humanFileSize(toDownloadBytes);
    const downloadAllText = props.isLocal ? 'Downloaded' : 'Download All';
    const chevronCSS = classNames({
      DatasetCard__chevron: true,
      'DatasetCard__chevron--expanded': state.expanded,
      'DatasetCard__chevron--collapsed': !state.expanded,
    });
    const unlinkPopupCSS = classNames({
      DatasetCard__popup: true,
      hidden: !state.unlinkPopupVisible || props.isLocked,
      Tooltip__message: true,
    });
    const commitsPopupCSS = classNames({
      DatasetCard__popup: true,
      hidden: !state.commitsPopupVisible || props.isLocked,
      Tooltip__message: true,
    });
    const commitsCSS = classNames({
      DatasetCard__commits: true,
      'DatasetCard__commits--loading': state.commitsPending,
    });
    const unlinkCSS = classNames({
      'Btn Btn__FileBrowserAction Btn__FileBrowserAction--unlink': true,
      'Btn__FileBrowserAction--loading': state.unlinkPending,

    });
    const downloadCSS = classNames({
      'Btn Btn__FileBrowserAction': true,
      'Btn__FileBrowserAction--downloaded Tooltip-data': props.isLocal,
      'Btn__FileBrowserAction--download': !props.isLocal,
      'Btn__FileBrowserAction--loading': state.downloadPending,
    });
    const progressCSS = classNames({
      'flex flex--column flex-1 DatasetCard__progress': true,
      'DatasetCard__progress--downloaded': toDownloadBytes === 0,
    });

    return (
      <div className="DatasetCard Card">
        <div
          className="DatasetCard__summary flex justify--space-between"
          onClick={evt => this._toggleExpanded(evt, !state.expanded)}
        >
          <div className={chevronCSS} />
          <div className="DatasetCard__info flex flex-1">
            <div className="DatasetCard__icon" />
            <div className="flex flex--column justify--space-between">
              <Link
                className="DatasetCard__name"
                to={`/datasets/${props.dataset.owner}/${props.dataset.name}`}
              >
                {props.dataset.name}
              </Link>
              <div className="DatasetCard__owner">{`by ${props.dataset.owner}`}</div>
              <div className="DatasetCard__details flex justify--space-between">
                <span>{sizeText}</span>
                <span>{numFilesText}</span>
              </div>
            </div>
          </div>
          <div className={progressCSS}>
            <progress
              value={onDiskBytes}
              max={props.dataset.overview.totalBytes}
            />
            <div className="flex justify--space-between">
              <div className="DatasetCard__onDisk flex flex--column">
                <div className="DatasetCard__onDisk--primary">{onDiskFormatted}</div>
                <div className="DatasetCard__onDisk--secondary">on disk</div>
              </div>
              {
                (toDownloadBytes !== 0)
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
        {
          state.expanded
          && (
          <DatasetBody
            files={props.formattedFiles.children}
            mutationData={props.mutationData}
            checkLocal={props.checkLocal}
            downloadPending={state.downloadPending}
            mutations={props.mutations}
            section={props.section}
          />
          )
        }
        {
          (props.dataset.commitsBehind > 0)
          && (
          <DatasetsCommits
            commitsCSS={commitsCSS}
            commitsPending={state.commitsPending}
            commitsBehind={props.dataset.commitsBehind}
            togglePopup={this._togglePopup}
            commitsPopupCSS={commitsPopupCSS}
            modifiyDatasetLink={this._modifyDatasetLink}
            tooltipShown={state.tooltipShown}
            toggleTooltip={() => this.setState({ tooltipShown: !state.tooltipShown })}
          />
          )
        }
      </div>
    );
  }
}
