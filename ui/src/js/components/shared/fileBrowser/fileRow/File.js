// vendor
import React, { Component } from 'react';
import Moment from 'moment';
import fileIconsJs from 'file-icons-js';
import classNames from 'classnames';
import { DragSource, DropTarget } from 'react-dnd';
import { NativeTypes } from 'react-dnd-html5-backend';
import TextTruncate from 'react-text-truncate';
// config
import config from 'JS/config';
// store
import store from 'JS/redux/store';
import { setMergeMode, updateTransitionState } from 'JS/redux/actions/labbook/labbook';
import { setErrorMessage, setInfoMessage, setWarningMessage } from 'JS/redux/actions/footer';
// mutations
import StartContainerMutation from 'Mutations/container/StartContainerMutation';
import StartDevToolMutation from 'Mutations/container/StartDevToolMutation';
// components
import ActionsMenu from './ActionsMenu';
import DatasetActionsMenu from './dataset/DatasetActionsMenu';
// utils
import Connectors from '../utilities/Connectors';
// assets
import './File.scss';

class File extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isDragging: props.isDragging,
      isSelected: (props.isSelected || (this.props.childrenState[this.props.fileData.edge.node.key] && this.props.childrenState[this.props.fileData.edge.node.key].isSelected)) || false,
      stateSwitch: false,
      newFileName: props.filename,
      renameEditMode: false,
      hover: false,
    };
    this._setSelected = this._setSelected.bind(this);
    this._renameEditMode = this._renameEditMode.bind(this);
    this._triggerMutation = this._triggerMutation.bind(this);
    this._clearState = this._clearState.bind(this);
    this._setHoverState = this._setHoverState.bind(this);
    this._checkHover = this._checkHover.bind(this);
  }

  static getDerivedStateFromProps(nextProps, state) {
    const isSelected = (nextProps.multiSelect === 'all')
      ? true
      : (nextProps.multiSelect === 'none')
        ? false
        : state.isSelected;

    if ((nextProps.isOverCurrent !== nextProps.isOverChildFile) && !nextProps.isDragging && state.hover) {
      nextProps.updateParentDropZone(nextProps.isOverCurrent);
    }
    return {
      ...state,
      isSelected,
    };
  }

  componentDidUpdate(prevProps, prevState, snapshot) {
    const { state } = this;
    if (state.renameEditMode) {
      this.reanmeInput.focus();
    }
  }

  /**
  *  @param {boolean} isSelected - sets if file has been selected
  *  sets elements to be selected and parent
  */
  _setSelected(evt, isSelected) {
    const { props } = this;
    props.updateChildState(props.fileData.edge.node.key, isSelected, false);
    this.setState({ isSelected }, () => {
      Object.keys(this.refs).forEach((ref) => {
        this.refs[ref].getDecoratedComponentInstance().getDecoratedComponentInstance()._setSelected();
      });
      if (props.checkParent) {
        props.checkParent();
      }
    });
  }

  /**
    *  @param {}
    *  sets dragging state
    */
  _mouseEnter() {
    if (this.props.setParentDragFalse) {
      this.props.setParentDragFalse();
    }
    if (this.state.isDragging && this.state.isHovered) {
      this.setState({ isDragging: true, isHovered: true });
    }
  }

  /**
    *  @param {String} devTool
    *  @param {Boolean} forceStart
    *  launches dev tool to appropriate file
    */
  _openDevTool(devTool, forceStart) {
    const { props } = this;
    const { owner, labbookName } = store.getState().routes;
    const status = props.containerStatus;
    const tabName = `${devTool}-${owner}-${labbookName}`;

    if ((status !== 'NOT_RUNNING') && (status !== 'RUNNING')) {
      setWarningMessage('Could not launch development environment as the project is not ready.');
    } else if (status === 'NOT_RUNNING' && !forceStart) {
      setInfoMessage('Starting Project container. When done working, click Stop to shutdown the container.');
      updateTransitionState(labbookName, 'Starting');
      setMergeMode(false, false);
      StartContainerMutation(
        owner,
        labbookName,
        (response, error) => {
          if (error) {
            setErrorMessage(`There was a problem starting ${labbookName} container`, error);
          } else {
            this._openDevTool(devTool, true);
          }
        },
      );
    } else {
      setInfoMessage(`Starting ${devTool}, make sure to allow popups.`);
      StartDevToolMutation(
        owner,
        labbookName,
        devTool,
        (response, error) => {
          if (response.startDevTool) {
            let path = `${window.location.protocol}//${window.location.hostname}${response.startDevTool.path}`;
            if (path.includes(`/lab/tree/${props.section}`)) {
              path = path.replace(`/lab/tree/${props.section}`, `/lab/tree/${props.section}/${props.fileData.edge.node.key}`);
            } else if (props.fileData.edge.node.key.indexOf('.Rmd') === -1) {
              path = `${path}/lab/tree/${props.section}/${props.fileData.edge.node.key}`;
            }

            window[tabName] = window.open(path, tabName);
            window[tabName].close();
            window[tabName] = window.open(path, tabName);
          }

          if (error) {
            setErrorMessage('Error Starting Dev tool', error);
          }
        },
      );
    }
  }

  /**
  *  @param {}
  *  sets dragging state
  */
  _mouseLeave() {
    const { props, state } = this;
    if (props.setParentDragTrue) {
      props.setParentDragTrue();
    }
    if (!state.isDragging && !state.isHovered) {
      this.setState({ isDragging: false, isHovered: false });
    }
  }

  /**
  *  @param {}
  *  sets dragging state to true
  */
  _checkHover() {
    const { state } = this;
    if (state.isHovered && !state.isDragging) {
      this.setState({ isDragging: true });
    }
  }

  /**
  *  @param {boolean} renameEditMode
  *  sets dragging state
  */
  _renameEditMode(renameEditMode) {
    this.setState({ renameEditMode });
  }

  /**
  *  @param {Object} evt
  *  sets dragging state
  */
  _updateFileName(evt) {
    this.setState({
      newFileName: evt.target.value,
    });
  }

  /**
  *  @param {Object} evt
  *  sets dragging state
  *  @return {}
  */
  _submitRename(evt, fileName) {
    if (evt.key === 'Enter' && this.state.newFileName !== fileName) {
      this._triggerMutation();
    }

    if (evt.key === 'Escape') {
      this._clearState();
    }
  }

  /**
  *  @param {}
  *  sets state on a boolean value
  *  @return {}
  */
  _clearState() {
    const { props } = this;
    this.setState({
      newFileName: props.filename,
      renameEditMode: false,
    });
  }

  /**
  *  @param {}
  *  triggers move mutation and clearState function
  *  @return {}
  */
  _triggerMutation() {
    const { props, state } = this;
    const fileKeyArray = props.fileData.edge.node.key.split('/');
    fileKeyArray.pop();
    const folderKeyArray = fileKeyArray;
    const folderKey = folderKeyArray.join('/');
    const newKey = (folderKey.length > 0)
      ? `${folderKey}/${state.newFileName}` : state.newFileName;

    this._clearState();
    if (props.fileData.edge.node.key !== newKey) {
      const data = {
        newKey: `${folderKey}/${state.newFileName}`,
        edge: props.fileData.edge,
        removeIds: [props.fileData.edge.node.id],
      };

      if (props.section !== 'data') {
        props.mutations.moveLabbookFile(data, (response) => {
          this._clearState();
        });
      } else {
        props.mutations.moveDatasetFile(data, (response) => {
          this._clearState();
        });
      }
    }
  }

  /**
  *  @param {object} event
  *  @param {boolean} hover - hover state for mouseover
  *  sets hover state
  *  @return {}
  */
  _setHoverState(evt, hover) {
    const { props, state } = this;
    evt.preventDefault();

    if (state.hover !== hover) {
      this.setState({ hover });
    }

    if (props.setParentHoverState && hover) {
      props.setParentHoverState(evt, !hover);
    }
  }

  render() {
    const { props, state } = this;
    const { node } = props.fileData.edge;
    const { index } = props.fileData;
    const fileName = props.filename;
    const cantDrag = !props.fileData.edge.node.isLocal && props.section === 'data'
    const isNotebook = fileName.split('.')[fileName.split('.').length - 1] === 'ipynb';
    // TODO remove hard coded references when api is updated
    const isRFile = fileName.split('.')[fileName.split('.').length - 1] === 'Rmd';
    const devTool = isNotebook ? 'JupyterLab' : isRFile ? 'Rstudio' : '';
    const paddingLeft = 40 * index;
    const rowStyle = { paddingLeft: `${paddingLeft}px` };

    // declare css here
    const fileRowCSS = classNames({
      File__row: true,
      'File__row--hover': state.hover,
      'File__row--noDrag': props.isDragging && cantDrag,
      'File__row--canDrag': props.isDragging && !cantDrag,
    });
    const buttonCSS = classNames({
      CheckboxMultiselect: true,
      CheckboxMultiselect__uncheck: !state.isSelected,
      CheckboxMultiselect__check: state.isSelected,
    });
    const textIconsCSS = classNames({
      'File__cell File__cell--name': true,
      hidden: state.renameEditMode,
    });
    const renameCSS = classNames({
      'File__cell File__cell--edit': true,
      hidden: !state.renameEditMode,
    });
    const truncateCSS = classNames({
      File__paragragh: true,
      'File__paragragh--external': isNotebook || isRFile,
    });

    const file = (
      <div
        style={this.props.style}
        onMouseOver={(evt) => { this._setHoverState(evt, true); }}
        onMouseOut={(evt) => { this._setHoverState(evt, false); }}
        onMouseLeave={() => { this._mouseLeave(); }}
        onMouseEnter={() => { this._mouseEnter(); }}
        className="File"
      >

        <div
          className={fileRowCSS}
          style={rowStyle}
        >
          {
            !props.readOnly
            && (
            <button
              type="button"
              className={buttonCSS}
              onClick={(evt) => { this._setSelected(evt, !this.state.isSelected); }}
            />
            )
          }
          <div className={textIconsCSS}>

            <div className={`File__icon ${fileIconsJs.getClass(fileName)}`} />

            <div className="File__text">
              { props.expanded
                && (
                <TextTruncate
                  className={truncateCSS}
                  line={1}
                  truncateText="…"
                  text={fileName}
                  onClick={() => {
                    if (isNotebook || isRFile) {
                      this._openDevTool(devTool);
                    }
                  }}
                />
                )
              }
            </div>
          </div>

          <div className={renameCSS}>

            <div className="File__container">
              <input
                draggable
                ref={(input) => { this.reanmeInput = input; }}
                value={this.state.newFileName}
                type="text"
                className="File__input"
                onClick={(evt) => { evt.preventDefault(); evt.stopPropagation(); }}
                onDragStart={(evt) => { evt.preventDefault(); evt.stopPropagation(); }}
                onChange={(evt) => { this._updateFileName(evt); }}
                onKeyDown={(evt) => { this._submitRename(evt, fileName); }}
              />
            </div>
            <div className="flex justify-space-around">
              <button
                type="button"
                className="File__btn--round File__btn--cancel File__btn--rename-cancel"
                onClick={() => { this._clearState(); }}
              />
              <button
                type="button"
                className="File__btn--round File__btn--add File__btn--rename-add"
                disabled={this.state.newFileName === fileName}
                onClick={() => { this._triggerMutation(); }}
              />
            </div>
          </div>

          <div className="File__cell File__cell--size">
            {config.humanFileSize(node.size)}
          </div>

          <div className="File__cell File__cell--date">
            {Moment((node.modifiedAt * 1000), 'x').fromNow()}
          </div>

          <div className="File__cell File__cell--menu">
            {
              !props.readOnly
              && (
              <ActionsMenu
                edge={props.fileData.edge}
                mutationData={props.mutationData}
                mutations={props.mutations}
                renameEditMode={this._renameEditMode}
                section={props.section}
              />
              )
            }
            {
              (props.section === 'data')
              && (
              <DatasetActionsMenu
                edge={props.fileData.edge}
                section={props.section}
                mutationData={props.mutationData}
                mutations={props.mutations}
                renameEditMode={this._renameEditMode}
                isDownloading={props.isDownloading}
                parentDownloading={props.parentDownloading}
                setFolderIsDownloading={props.setFolderIsDownloading}
                isLocal={props.fileData.edge.node.isLocal}
                isDragging={props.isDragging}
              />
              )
            }
          </div>

        </div>
      </div>
    );

    if (!props.readOnly) {
      return (
        props.connectDragSource(file)
      );
    }
    return file;
  }
}

const FileDnD = DragSource(
  'card',
  Connectors.dragSource,
  Connectors.dragCollect,
)((File));


export default FileDnD;
