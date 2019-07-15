// vendor
import React, { Component } from 'react';
import { NativeTypes } from 'react-dnd-html5-backend';
import { boundMethod } from 'autobind-decorator';
import { DropTarget } from 'react-dnd';
import classNames from 'classnames';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// assets
import './Requirements.scss';

class Requirements extends Component {

  state = {
    rejectedPackages: [],
    droppedFile: null,
    fileParsing: false,
  }

  /**
  *  @param {Object} file
  *  parses requirements file
  *  @return {}
  */
  @boundMethod
  _parseFile(file) {
    const { props, state } = this;
    const self = this;
    const reader = new FileReader();
    if (!state.droppedFile) {
      if (file.type === 'text/plain') {
        this.setState({ droppedFile: file.name, fileParsing: true });
        reader.onload = (evt) => {
          const rejectedPackages = [];
          const packages = evt.target.result.split('\n').filter(line => (line[0] !== '#') && (line !== ''));
          packages.forEach((pkg) => {
            const splitPackage = pkg.split('==');
            if (/ |\[| \]|=/.test(splitPackage[0])) {
              rejectedPackages.push(pkg);
            } else {
              const packageData = {
                manager: 'pip',
                package: splitPackage[0],
                version: splitPackage[1],
              };
              props.queuePackage(packageData);
            }
            self.setState({ rejectedPackages, droppedFile: file.name, fileParsing: false });
          });
        };
        reader.readAsText(file);
      } else {
        setErrorMessage('Requirements file must be a text file');
      }
    }
  }

  render() {
    const { props, state } = this;
    const dropBoxCSS = classNames({
      'Dropbox flex flex--column align-items--center': true,
      'Dropbox--hovered': props.isOver,
    });
    const fileDroppedCSS = classNames({
      'Requirements__dropped-file Card Card--no-hover Card--requirements': true,
      'Requirements__dropped-file--loading': state.fileParsing,
    })
    const subText = props.isOver ? '' : 'or';
    return props.connectDropTarget(
      <div className="Requirements__file flex justify--center">
        {
          !state.droppedFile
          && (
          <div
            className={dropBoxCSS}
          >
            <div className="Dropbox--menu">
              Drag and drop pip requirements.txt file here
              <br />
              {subText}
            </div>
            {
              !props.isOver
              && (
              <label
                htmlFor="requirements_upload"
                className="Requirements__label"
              >
                <div
                  className="Btn Btn--allStyling"
                >
                  Choose Files...
                </div>
                <input
                  id="requirements_upload"
                  className="hidden"
                  type="file"
                  onChange={evt => this._parseFile(evt.target.files[0])}
                />
              </label>
              )
            }
          </div>
          )
        }
        {
          state.droppedFile
          && (
          <div className={fileDroppedCSS}>
            <div className="Requirements__file-name">
              {state.droppedFile}
            </div>
            {
              state.rejectedPackages.length > 0 && (
              <div className="Requirements__rejectedPackages">
                The following packages could not be installed:
                {
                  state.rejectedPackages.map(rejectedPackage => (
                    <div
                      className="Requirements__rejected-package"
                      key={rejectedPackage}
                    >
                      {rejectedPackage}
                    </div>
                  ))
                }
              </div>
              )
            }
          </div>
          )
        }
      </div>,
    );
  }
}

const fileTarget = {
  drop(props, monitor, component) {
    if (monitor.getItem().files.length === 1) {
      component._parseFile(monitor.getItem().files[0]);
    }
  },
};


export default DropTarget(NativeTypes.FILE, fileTarget, (connect, monitor) => ({
  connectDropTarget: connect.dropTarget(),
  isOver: monitor.isOver(),
  canDrop: monitor.canDrop(),
}))(Requirements);
