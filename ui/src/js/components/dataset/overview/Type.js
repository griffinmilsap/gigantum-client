// vendor
import React, { Component } from 'react';
// assets
import './Type.scss';

export default class Type extends Component {
  render() {
    const { type, isManaged } = this.props;
    return (
      <div className="Type">
        <div className="Type__info grid">
          <div className="Type__card Card--auto Card--no-hover column-1-span-12">
            <div className="Type__imageContainer">
              <img
                className="Type__image"
                height="50"
                width="50"
                src={`data:image/jpeg;base64,${type.icon}`}
                alt={type.name}
              />
            </div>

            <div className="Type__cardText">
              <div className="Type__title">
                <h6 className="Type__name">{type.name}</h6>
              </div>
              <div>
                <p className="Type__paragraph">{type.description}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
