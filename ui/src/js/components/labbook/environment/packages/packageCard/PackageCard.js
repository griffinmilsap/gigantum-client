// vendor
import React, { Component } from 'react';
import { boundMethod } from 'autobind-decorator';
// components
import AdvancedSearch from 'Components/common/advancedSearch/AdvancedSearch';
import PackageHeader from './PackageHeader';
import PackageBody from './PackageBody';
// assets
import './PackageCard.scss';

/**
  @param {Object} node
  flattens node values into a string to make it searchable
*/
const flattenCombineNodeValues = ((node) => {
  let lowercaseJSON = '';
  Object.keys(node).forEach((key) => {
    if (typeof node[key] === 'string') {
      lowercaseJSON += `${node[key].toLowerCase()} /n`;
    }
  });
  return lowercaseJSON;
});

/**
  @param {Object} node
  @param {Array} tags
  @param {String} lowercaseJSON
  @param {Boolean} isReturned
  searches node for tags and returns true is there is a match;
*/
const searchTagsForMatch = ((node, tags, lowercaseJSON, isReturned) => {
  let newIsReturned = isReturned;
  tags.forEach(({ text, className }) => {
    if (className === 'Package Manager') {
      if (node.manager.indexOf(text) === -1) {
        newIsReturned = false;
      }
    } else if (lowercaseJSON.indexOf(text.toLowerCase()) === -1) {
      newIsReturned = false;
    }
  });

  return newIsReturned;
});


/**
  *  @param {Object} packages
  *  @param {Array} tags
  * filters packages
  */

const filterPackages = (packages, tags) => {
  const filteredPackages = packages.filter((node) => {
    const lowercaseJSON = flattenCombineNodeValues(node);
    let isReturned = true;
    isReturned = searchTagsForMatch(node, tags, lowercaseJSON, isReturned);
    return isReturned;
  });
  return filteredPackages;
};

/**
  *  @param {String} sort
  *  @param {Boolean} reverse
  *  @param {String} search
  *  @param {Object} packages
  *  @param {Array} tags
  *  sorts and filters packages
  */

const sortPackages = (sort, reverse, search, packages, tags) => {
  const remainingPackages = filterPackages(packages, tags);
  const newPackages = remainingPackages.slice().sort((a, b) => {
    if (a[sort].toLowerCase() > b[sort].toLowerCase()) {
      return reverse ? -1 : 1;
    }
    return reverse ? 1 : -1;
  });
  return newPackages;
};

export default class PackageCard extends Component {
  state = {
    selectedPackages: new Map(),
    sort: 'package',
    reverse: false,
    tags: [],
  }


  /**
    @param {Array} tags
    sets component tags from child
  */
  @boundMethod
  _setTags(tags) {
    this.setState({ tags });
  }

  /**
  *  @param {String} sort
  *  sets sort state
  */
  @boundMethod
  _handleSort(sort) {
    const { state } = this;

    if (sort === state.sort) {
      this.setState({ reverse: !state.reverse });
    } else {
      this.setState({ sort, reverse: false });
    }
  }

  /**
  *  @param {Boolean} forceClear
  *  toggles selectedPackages
  */
  @boundMethod
  _selectPackages(forceClear) {
    const { props, state } = this;
    const packageEdges = props.packages;
    if (state.selectedPackages.size === packageEdges.length || forceClear) {
      this.setState({ selectedPackages: new Map() });
    } else {
      const newSelectedPackages = new Map();
      packageEdges.forEach((edge) => {
        if (!edge.fromBase) {
          newSelectedPackages.set(edge.id, edge);
        }
      });
      this.setState({ selectedPackages: newSelectedPackages });
    }
  }

  /**
  *  @param {Object} pkg
  *  adds or removes package from selectedPackages
  */
  @boundMethod
  _selectSinglePackage(pkg) {
    const { state } = this;
    const hasPackage = state.selectedPackages.has(pkg.id);
    const newSelectedPackages = new Map(state.selectedPackages);
    if (hasPackage) {
      newSelectedPackages.delete(pkg.id);
    } else {
      newSelectedPackages.set(pkg.id, pkg);
    }
    this.setState({ selectedPackages: newSelectedPackages });
  }

  render() {
    const { props, state } = this;
    const selectedLength = state.selectedPackages.size;
    const propsLength = props.packages.length;
    let multiSelect = selectedLength === propsLength ? 'all' : 'partial';
    multiSelect = selectedLength === 0 ? 'none' : multiSelect;
    const packages = sortPackages(state.sort, state.reverse, state.search, props.packages, state.tags);
    const { packageManagers } = props.base;
    const filterCategories = {
      'Package Managers': packageManagers,
    };

    return (
      <div className="PackageCard Card Card--auto Card--no-hover column-1-span-12 relative">
        <button
          type="button"
          disabled={props.isLocked}
          onClick={() => props.togglePackageModal(true)}
          className="Btn Btn--feature Btn--feature--expanded Btn--feature--expanded--paddingLeft Btn__plus Btn__plus--featurePosition"
        >
          Add Package
        </button>
        <AdvancedSearch
          tags={state.tags}
          setTags={this._setTags}
          filterCategories={filterCategories}
          customStyle="packages"
          autoHide
        />
        <PackageHeader
          handleSort={this._handleSort}
          multiSelect={multiSelect}
          selectPackages={this._selectPackages}
          selectedPackages={state.selectedPackages}
          packages={packages}
          sort={state.sort}
          reverse={state.reverse}
          packageMutations={props.packageMutations}
          isLocked={props.isLocked}
          buildCallback={props.buildCallback}
          setBuildingState={props.setBuildingState}
        />
        <PackageBody
          packages={packages}
          isLocked={props.isLocked}
          selectPackages={this._selectPackages}
          selectedPackages={state.selectedPackages}
          selectSinglePackage={this._selectSinglePackage}
          packageMutations={props.packageMutations}
          buildCallback={props.buildCallback}
          setBuildingState={props.setBuildingState}
        />
      </div>
    );
  }
}
