// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// assets
import './SecretsActions.scss';

export default class SecretsAction extends Component {
  state = {
    popupVisible: false,
  }

  /**
  *  @param {}
  *  triggers delete secret mutation
  *  @return {}
  */
  _deleteSecret = () => {
    const { props } = this;
    const data = {
      filename: props.filename,
      id: props.id,
    };

    const deleteCallback = (response, error) => {
      if (error) {
        setErrorMessage('An error occured while attempting to delete secrets file', error);
      }
    };

    const removeCallback = () => {
      props.secretsMutations.removeSecret(data, deleteCallback);
    };

    props.secretsMutations.deleteSecret(data, removeCallback);
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

  render() {
    const { state, props } = this;
    const popupCSS = classNames({
      SecretsActions__popup: true,
      hidden: !state.popupVisible || props.isEditing,
      Tooltip__message: true,
    });
    return (
      <div className="SecretsAction flex justify--space-around align-items--end">
        <div className="relative">
          <button
            className="Btn Btn--medium Btn--noMargin Btn--round Btn__delete-secondary Btn__delete-secondary--medium"
            type="button"
            onClick={(evt) => { this._togglePopup(evt, true); }}
            disabled={props.isEditing}
          />
          <div className={popupCSS}>
            <div className="Tooltip__pointer" />
            <p className="margin-top--0">Are you sure?</p>
            <div className="flex justify--space-around">
              <button
                className="Secrets__btn--round Secrets__btn--cancel"
                onClick={(evt) => { this._togglePopup(evt, false); }}
                type="button"
              />
              <button
                className="Secrets__btn--round Secrets__btn--add"
                onClick={this._deleteSecret}
                type="button"
              />
            </div>
          </div>
        </div>
        <button
          className="Btn Btn--medium Btn--noMargin Btn--round Btn__edit-secondary Btn__edit-secondary--medium"
          type="button"
          onClick={() => props.editSecret(props.filename)}
        />
      </div>
    );
  }
}
