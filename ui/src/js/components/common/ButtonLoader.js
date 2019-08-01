// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// assets
import './ButtonLoader.scss';

export default class ButtonLoader extends Component {
  /** **
   * @param {object, object}
   * checks button state
   * passes back to callback
   * return {}
   ***** */
  _clickCallback = (evt, params) => {
    const { props } = this;
    props.clicked(evt, params);
  }

  render() {
    const { props } = this;
    const {
      buttonState,
      buttonText,
      buttonDisabled,
    } = props;
    const buttonTestToDisplay = buttonState !== 'finished' ? buttonText : '✓';
    // declare css here
    const buttonLoaderCSS = classNames({
      'Btn ButtonLoader': true,
      [`ButtonLoader--${buttonState}`]: buttonState !== '',
      [props.className]: (props.className !== null),
    });
    const buttonLoaderIconCSS = classNames({
      ButtonLoader__icon: true,
      hidden: buttonState !== 'loading',
    });

    return (
      <button
        type="submit"
        disabled={buttonState !== '' || buttonDisabled}
        data-tooltip={props['data-tooltip']}
        className={buttonLoaderCSS}
        onClick={evt => props.clicked(evt, props)}
      >
        <div className={buttonLoaderIconCSS} />
        {buttonTestToDisplay}
      </button>
    );
  }
}
