// vendor
import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
// assets
import './ActionsMenu.scss';

export default class ActionsMenu extends Component {
  constructor(props) {
  	super(props);
  	this._closePopup = this._closePopup.bind(this);
    this._setWrapperRef = this._setWrapperRef.bind(this);
  }

  state = {
    popupVisible: false,
  }

  /**
  *  LIFECYCLE MEHTODS START
  */
  componentWillMount() {
    window.removeEventListener('click', this._closePopup);
  }

  componentDidMount() {
    window.addEventListener('click', this._closePopup);
  }
  /**
  *  LIFECYCLE MEHTODS END
  */

  /**
  *  @param {Object} event
  *  closes popup when clicking
  *  @return {}
  */
  _closePopup(evt) {
    if (this.state.popupVisible && this[this.props.edge.node.id] && !this[this.props.edge.node.id].contains(evt.target)) {
      this.setState({ popupVisible: false });
    }
  }

  /**
  *  @param {Obect} evt
  *  @param {boolean} popupVisible - boolean value for hiding and showing popup state
  *  triggers favoirte unfavorite mutation
  *  @return {}
  */
  _togglePopup(evt, popupVisible) {
    if (!popupVisible) {
      evt.stopPropagation(); // only stop propagation when closing popup, other menus won't close on click if propagation is stopped
    }
    this.setState({ popupVisible });
  }

  /**
  *  @param {Object} data - event from clicking delete button
  *  triggers DeleteLabbookFileMutation
  *  @return {}
  */
  _getEdges(data) {
    const edges = [data.edge];
    function getEdges(data) {
      Object.keys(data).forEach((name) => {
        edges.push(data[name].edge);
        if (data[name].children) {
          getEdges(data[name].children);
        }
      });
      return edges;
    }
    if (data.children) {
      getEdges(data.children);
    }
    return edges;
  }

  /**
  *  @param {event} evt - event from clicking delete button
  *  triggers DeleteLabbookFileMutation
  *  @return {}
  */
  _triggerDeleteMutation(evt) {
    const edges = this.props.fileData ? this._getEdges(this.props.fileData) : [this.props.edge];
    const deleteFileData = {
      filePaths: [this.props.edge.node.key],
      edges,
    };

    this.props.mutations.deleteLabbookFiles(deleteFileData, (reponse) => {});

    this._togglePopup(evt, false);
  }

  /**
  *  @param {Object} node - Dom object to be assigned as a ref
  *  set wrapper ref
  *  @return {}
  */
  _setWrapperRef(node) {
    this[this.props.edge.node.id] = node;
  }

  render() {
    const { props, state } = this;
    const disableButtons = props.section === 'data' && (!props.edge.node.isLocal || (props.folder && !props.isLocal));
    const deleteTooltip = disableButtons ? 'Must download before deleting' : 'Delete';
    const renameTooltip = disableButtons ? 'Must download before renaming' : 'Rename';
    const isUntrackedDirectory = (props.edge.node.key === 'untracked/') && props.folder && (props.section === 'output');

    const popupCSS = classNames({
      ActionsMenu__popup: true,
      hidden: !state.popupVisible,
      Tooltip__message: true,
    });
    const deleteCSS = classNames({
      'ActionsMenu__item Btn Btn--fileBrowser Btn__delete-secondary Btn--round': true,
      'Tooltip-data Tooltip-data--small': !state.popupVisible,
      'ActionsMenu__popup-visible': state.popupVisible,
    });
    const folderCSS = classNames({
      'ActionsMenu__item Btn Btn--fileBrowser Tooltip-data Tooltip-data--small Btn--round': true,
      Btn__addFolder: true,
      'visibility-hidden': !props.folder,
    });

    return (
      <div
        className="ActionsMenu"
        key={`${props.edge.node.id}-action-menu}`}
        ref={this._setWrapperRef}
      >
        <button
          disabled={props.edge.node.key === 'untracked/'}
          onClick={() => { props.folder && props.addFolderVisible(true); }}
          className={folderCSS}
          data-click-id="addFolder"
          data-tooltip="Add Subfolder"
          type="button"
        />
        {
            !isUntrackedDirectory
            && (
            <Fragment>
              <div className="relative">
                <button
                  className={deleteCSS}
                  data-tooltip={deleteTooltip}
                  onClick={(evt) => { this._togglePopup(evt, true); }}
                  disabled={disableButtons}
                  type="button"
                />
                <div className={popupCSS}>
                  <div className="Tooltip__pointer" />
                  <p>Are you sure?</p>
                  <div className="flex justify--space-around">
                    <button
                      className="File__btn--round File__btn--cancel"
                      onClick={(evt) => { this._togglePopup(evt, false); }}
                      type="button"
                    />
                    <button
                      className="File__btn--round File__btn--add"
                      onClick={(evt) => { this._triggerDeleteMutation(evt); }}
                      type="button"
                    />
                  </div>
                </div>
              </div>
              <button
                disabled={disableButtons}
                onClick={() => { props.renameEditMode(true); }}
                className="ActionsMenu__item Btn Btn--fileBrowser Btn__rename Tooltip-data Tooltip-data--small Btn--round"
                data-tooltip={renameTooltip}
                type="button"
              />
            </Fragment>
            )
          }
      </div>
    );
  }
}
