// vendor
import React, { Component } from 'react';
import ReactMarkdown from 'react-markdown';
import classNames from 'classnames';
// assets
import './BaseCard.scss';

export default class DatasetSlide extends Component {
  state = {
    expanded: false,
  }

  /**
  * @param {} -
  * sets details view to expanded
  * return {}
  */
  _setBooleanState(evt, type) {
    const { state } = this;
    evt.preventDefault();
    evt.stopPropagation();

    this.setState({ [type]: !state[type] });
  }

  render() {
    const { props, state } = this;
    const { node } = props;
    const selectedBaseImage = classNames({
      'BaseCard Card': true,
      'BaseCard--selected': (props.selectedBaseId === node.id),
      'BaseCard--expanded': state.expanded,
    });
    const actionCSS = classNames({
      'BaseCard-actions': true,
      'BaseCard-actions--expanded': state.expanded,
    });

    return (<div
      onClick={evt => props.selectBase(node)}
      className="BaseCard-wrapper">
      <div className={selectedBaseImage}>
        <div className="BaseCard__icon">
          <img
            alt=""
            src={`data:image/jpeg;base64,${node.icon}`}
            height="50"
            width="50"
          />
        </div>
        <div className="BaseCard__details">
          <h6 className="BaseCard__name">{node.name}</h6>
          <p className="BaseCard__type">{node.isManaged ? 'Managed' : 'Unmanaged'}</p>
        </div>
        <div className="BaseCard__moreDetails">
          <p className="BaseCard__description-description">{node.description}</p>
          { (state.expanded)
            && <div>
                <hr/>
                <ReactMarkdown
                  className="BaseCard__readme Readme"
                  source={node.readme}
                />
               </div>
          }
        </div>
        <div className={actionCSS}>
          <button
             onClick={(evt) => { this._setBooleanState(evt, 'expanded'); }}
             className="Btn Btn__dropdown Btn--flat">
          </button>
        </div>
      </div>
    </div>);
  }
}
