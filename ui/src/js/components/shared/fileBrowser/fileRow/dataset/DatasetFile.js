// vendor
import React, { Component } from 'react';
import Moment from 'moment';
import fileIconsJs from 'file-icons-js';
import classNames from 'classnames';
import TextTruncate from 'react-text-truncate';
// config
import config from 'JS/config';
// components
import ActionsMenu from './DatasetActionsMenu';
// assets
import './DatasetFile.scss';

class File extends Component {
  render() {
    const { props } = this;
    const { node } = props.fileData.edge;
    const { index } = props.fileData;
    const fileName = props.filename;
    const fileRowCSS = classNames({
      File__row: true,
    });

    const textIconsCSS = classNames({
      'File__cell File__cell--name': true,
    });

    const paddingLeft = 40 * index;


    const rowStyle = { paddingLeft: `${paddingLeft}px` };
    return (
      <div
        style={props.style}
        className="File"
      >
        <div
          className={fileRowCSS}
          style={rowStyle}
        >

          <div className={textIconsCSS}>

            <div className={`File__icon ${fileIconsJs.getClass(fileName)}`} />

            <div className="File__text">
              {
                props.expanded
                && (
                  <TextTruncate
                    className="File__paragragh"
                    line={1}
                    truncateText="…"
                    text={fileName}
                  />
                )
               }
            </div>

          </div>

          <div className="File__cell File__cell--size">
            {config.humanFileSize(node.size)}
          </div>

          <div className="File__cell File__cell--date">
            {Moment((node.modifiedAt * 1000), 'x').fromNow()}
          </div>

          <div className="File__cell File__cell--menu">
            <ActionsMenu
              section={props.section}
              edge={props.fileData.edge}
              isLocal={props.fileData.edge.node.isLocal}
              mutationData={props.mutationData}
              mutations={props.mutations}
              renameEditMode={this._renameEditMode}
              isDownloading={props.isDownloading}
            />
          </div>
        </div>
      </div>
    );
  }
}


export default File;
