// vendor
import React, { Component, Fragment } from 'react';
import ReactDom from 'react-dom';
import classNames from 'classnames';
// assets
import './Modal.scss';

export default class Modal extends Component {
  componentDidMount() {
    if (document.getElementById('root')) {
      document.getElementById('root').classList.add('no-overflow');
    }
  }

  componentWillUnmount() {
    if (document.getElementById('root')) {
      document.getElementById('root').classList.remove('no-overflow');
    }
  }

  render() {
    const { props } = this;
    const modalContentCSS = classNames({
      Modal__content: true,
      [`Modal__content--${props.size}`]: props.size, // large, medium, small
      [props.icon]: !!props.icon,
    });
    const modalContainerCSS = classNames({
      'Modal__sub-container': true,
      'Modal__sub-container--nopadding': props.noPadding,
    });
    const overflow = (props.overlfow === 'visible') ? 'visible' : 'hidden';

    return (
      ReactDom.createPortal(
        <div className="Modal">
          <div
            className="Modal__cover"
            onClick={props.handleClose}
          />

          <div className={modalContentCSS} style={{ overflow }}>
            { props.handleClose
              && (
              <button
                type="button"
                className="Btn Btn--flat Modal__close padding--small "
                onClick={() => props.handleClose()}
              />
              )
            }
            <div className="Modal__container">
              { props.preHeader
                && <p className="Modal__pre-header">{props.preHeader}</p>
              }
              { props.header
                && (
                <Fragment>
                  <h1 className="Modal__header">
                    <div className={`Icon Icon--${props.icon}`} />
                    {props.header}
                  </h1>
                  <hr />
                </Fragment>
                )
              }
              <div className={modalContainerCSS}>{props.renderContent()}</div>
            </div>
          </div>
        </div>,
        document.getElementById('modal'),
      )
    );
  }
}
