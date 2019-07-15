// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { boundMethod } from 'autobind-decorator';
// components
import Loader from 'Components/common/Loader';
// assets
import './SectionWrapper.scss';

const getComponetPaths = ((props) => {
  const sectionType = props.labbook ? 'labbook' : 'dataset';
  const sectionPathRoot = `${sectionType}`;
  const sectionUpperCase = props.section[0].toUpperCase() + props.section.slice(1);
  const section = ((props.section === 'code') || props.section === 'data') ? props.section : `${props.section}Data`;
  const browserPath = `${sectionPathRoot}/${section}/${sectionUpperCase}Browser`;

  return ({
    browserPath,
  });
});

export default class SectionWrapper extends Component {
  state = {
    selectedFiles: [],
  };

  componentDidMount() {
    const { props } = this;
    const { section } = props;
    props.refetch(section);
  }

  /**
  *  @param {Object} evt
  *  set state with selected filter
  *  @return {}
  */
  @boundMethod
  _setSelectedFiles(evt) {
    const files = [...evt.target.files];
    this.setState({ selectedFiles: files });
  }

  /**
  *  @param {}
  *  clear selected files
  *  @return {}
  */
  @boundMethod
  _clearSelectedFiles() {
    this.setState({ selectedFiles: [] });
  }

  /**
  *  @param {Object} result
  *  udate loading status if state is not the same as result
  *  @return {}
  */
  @boundMethod
  _loadStatus(result) {
    const { state } = this;
    if (result !== state.loadingStatus) {
      this.setState({ loadingStatus: result });
    }
  }

  render() {
    const { props, state } = this;
    const sectionObject = props.labbook || props.dataset;
    const innerSection = props.dataset ? sectionObject : sectionObject[props.section];
    const {
      browserPath,
    } = getComponetPaths(props);

    if (sectionObject) {
      const sectionId = props.labbookId || props.datasetId;
      const { section } = props;
      const Browser = require(`./../../../${browserPath}`).default;

      // declare css
      const sectionProps = {
        [section]: innerSection,
      };
      if (!((section === 'data') || (sectionObject[section]))) {
        return <Loader />;
      }

      if (!((section === 'data' && sectionObject.id) || (sectionObject[section]))) {
        return <Loader />;
      }

      return (

        <div className="SectionWrapper">
          {
            (props.section === 'input')
            && <h4 className="margin-bottom--0 regular">Datasets and Files</h4>
          }
          <div className="grid">
            <div className="SectionWrapper__file-browser column-1-span-12">
              <Browser
                selectedFiles={state.selectedFiles}
                clearSelectedFiles={this._clearSelectedFiles}
                labbookId={sectionId}
                sectionId={innerSection.id}
                section={section}
                loadStatus={this._loadStatus}
                isLocked={props.isLocked}
                isManaged={props.isManaged}
                owner={props.owner}
                name={props.name}
                {...sectionProps}
                linkedDatasets={sectionObject.linkedDatasets || null}
                containerStatus={props.containerStatus}
                lockFileBrowser={props.lockFileBrowser}

              />
            </div>
          </div>
        </div>
      );
    }
    return (<div>No Files Found</div>);
  }
}
