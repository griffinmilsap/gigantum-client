// vendor
import React, { Component } from 'react';
import { createPaginationContainer, graphql } from 'react-relay';
import classNames from 'classnames';
import uuidv4 from 'uuid/v4';
import { connect } from 'react-redux';
import { boundMethod } from 'autobind-decorator';
// store
import store from 'JS/redux/store';
import {
  setPackageMenuVisible,
} from 'JS/redux/reducers/labbook/environment/packageDependencies';
import { setErrorMessage, setWarningMessage } from 'JS/redux/reducers/footer';
import { setContainerMenuWarningMessage } from 'JS/redux/reducers/labbook/environment/environment';
import { setBuildingState } from 'JS/redux/reducers/labbook/labbook';
import { setLookingUpPackagesState } from 'JS/redux/reducers/labbook/containerStatus';
// Mutations
import AddPackageComponentsMutation from 'Mutations/environment/AddPackageComponentsMutation';
import RemovePackageComponentsMutation from 'Mutations/environment/RemovePackageComponentsMutation';
// config
import config from 'JS/config';
// components
import ButtonLoader from 'Components/common/ButtonLoader';
import Loader from 'Components/common/Loader';
// helpers
import PackageLookup from './PackageLookup';
// assets
import './PackageDependencies.scss';


let owner;
let updateCheck = {};

class PackageDependencies extends Component {
  constructor(props) {
    super(props);

    const { labbookName } = store.getState().routes;
    owner = store.getState().routes.owner; // TODO clean this up when fixing dev environments

    this.state = {
      owner,
      labbookName,
      selectedTab: '',
      packageMenuVisible: false,
      packageName: '',
      version: '',
      packages: [],
      searchValue: '',
      forceRender: false,
      disableInstall: false,
      installDependenciesButtonState: '',
      hardDisable: false,
      removalPackages: {},
      updatePackages: {},
      latestVersionPackages: [],
      currentPackages: this.props.environment.packageDependencies,
    };
  }

  static getDerivedStateFromProps(props, state) {

    const packages = props.environment.packageDependencies.edges;

    let latestVersionPackages = packages.map((edge) => {
      let packageObject = { ...edge.node };
      if (props.packageLatestVersions.length > 0) {
        props.packageLatestVersions.forEach((latestVersionEdge) => {
          if ((packageObject.manager === latestVersionEdge.node.manager) && (packageObject.package === latestVersionEdge.node.package)) {
            packageObject.latestVersion = latestVersionEdge.node.latestVersion;
          }
        });
      }
      return packageObject;
    });

    return {
      ...state,
      latestVersionPackages,
    };
  }

  componentDidUpdate() {
    const { props, state } = this;
    const newPackages = this.props.environment.packageDependencies;
    if (newPackages.edges && (newPackages.edges.length < 11) && newPackages.pageInfo.hasNextPage && !state.loadingMore) {
      this._loadMore();
    }

    const newUpdatePackages = Object.assign({}, this.state.updatePackages, updateCheck);
    Object.keys(newUpdatePackages).forEach((manager) => {
      Object.keys(newUpdatePackages[manager]).forEach((pkg) => {
        if (!newUpdatePackages[manager][pkg].version) {
          delete newUpdatePackages[manager][pkg];
        }
      });
    });

    if (JSON.stringify(newUpdatePackages) !== JSON.stringify(this.state.updatePackages)) {
      this.setState({ updatePackages: newUpdatePackages });
    }
    updateCheck = {};
  }

  /*
    handle state and addd listeners when component mounts
  */
  componentDidMount() {
    const { props, state } = this;

    // if (props.environment.packageDependencies.pageInfo.hasNextPage) {
    //   this._loadMore(); // routes query only loads 2, call loadMore
    // }

    if (state.selectedTab === '') {
      this.setState({ selectedTab: props.base.packageManagers[0] });
    }
  }

  /**
  *  @param{}
  *  triggers relay pagination function loadMore
  *  increments by 10
  *  logs callback
  */
  @boundMethod
  _loadMore() {
    if (!this.state.loadingMore) {
      this.setState({ loadingMore: true });

      const self = this,
            { props } = this;
      props.relay.loadMore(
        10, // Fetch the next 5 feed items
        (response, error) => {
          self.setState({ loadingMore: false });

          if (error) {
            console.error(error);
          }
          if (props.environment.packageDependencies &&
           props.environment.packageDependencies.pageInfo.hasNextPage) {
            self._loadMore();
          }
        },
        {
          cursor: props.environment.packageDependencies.pageInfo.endCursor,
        },
      );
    }
  }

  /**
  *  @param {Object}
  *  hides packagemanager modal
  */
  @boundMethod
  _setSelectedTab(selectedTab, isSelected) {
    const { props, state } = this,
          packageMenuVisible = isSelected ? props.packageMenuVisible : false,
          packages = isSelected ? state.packages : [];

    this.setState({
      selectedTab,
      packageMenuVisible,
      packages,
    });
  }
  /**
  *  @param {object} node
  *  triggers remove package mutation
  */
  _removePackage() {
    const { status } = store.getState().containerStatus,
          self = this,
          { props } = this,
          canEditEnvironment = config.containerStatus.canEditEnvironment(status) && !props.isLocked;

    this.setState({ hardDisable: true });
    // have to get state after setting state
    const { state } = this;

    if (navigator.onLine) {
      if (canEditEnvironment) {
        if (!state.hardDisable) {
          const { labbookName, owner } = store.getState().routes,
                { environmentId } = props,
                manager = state.selectedTab,
                removalPackages = Object.keys(state.removalPackages[manager]),
                removalIDArr = Object.values(state.removalPackages[manager]),
                clientMutationId = uuidv4(),
                connection = 'PackageDependencies_packageDependencies'

          this.setState({ removalPackages: {}, updatePackages: {} });

          RemovePackageComponentsMutation(
            labbookName,
            owner,
            manager,
            removalPackages,
            removalIDArr,
            clientMutationId,
            environmentId,
            connection,
            (response, error) => {
              if (error) {
                console.log(error);
              }

              this.setState({ hardDisable: false });
              props.buildCallback();
            },
          );
        }
      } else {
        this._promptUserToCloseContainer();
        this.setState({ hardDisable: false });
      }
    } else {
      props.setErrorMessage('Cannot remove package at this time.', [{ message: 'An internet connection is required to modify the environment.' }]);
    }
  }
  /**
  *  @param {object} node
  *  triggers remove package mutation
  */
  _toggleAddPackageMenu() {
    const { status } = store.getState().containerStatus;
    const canEditEnvironment = config.containerStatus.canEditEnvironment(status) && !this.props.isLocked;

    if (navigator.onLine) {
      if (canEditEnvironment) {
        this.props.setPackageMenuVisible(!this.props.packageMenuVisible);
      } else {
        this._promptUserToCloseContainer();
      }
    } else {
      this.props.setErrorMessage('Cannot add package at this time.', [{ message: 'An internet connection is required to modify the environment.' }]);
    }
  }
  /**
  *  @param {evt}
  *  updates package name in components state
  */
  _updatePackageName(evt) {
    this.setState({ packageName: evt.target.value });

    if (evt.key === 'Enter' && evt.target.value.length) {
      this._addStatePackage(evt);
    }
  }

  /**
  *  @param {evt}
  *  updates package version in components state
  */
  _updateVersion(evt) {
    this.setState({ version: evt.target.value });

    if (evt.key === 'Enter') {
      this._addStatePackage(evt);
    }
  }
  /**
  *  @param {}
  *  updates packages in state
  */
  _addStatePackage() {
    const packages = this.state.packages;

    const { packageName, version } = this.state;
    const manager = this.state.selectedTab;

    packages.push({
      package: packageName,
      version,
      manager,
      validity: 'valid',
    });

    this.setState({
      packages,
      packageName: '',
      version: '',
    });

    this.inputPackageName.value = '';
    this.inputVersion.value = '';
  }

  /**
  *  @param {}
  *  user redux to open stop container button
  *  sends message to footer
  */
  _promptUserToCloseContainer() {
    this.props.setContainerMenuWarningMessage('Stop Project before editing the environment. \n Be sure to save your changes.');
  }
  /**
  *  @param {}
  *  updates packages in state
  */
  _removeStatePackages(node, index) {
    const packages = this.state.packages;

    packages.splice(index, 1);

    this.setState({
      packages,
    });
  }
  /**
  *  @param {}
  *  triggers add package mutation
  */
  @boundMethod
  _addPackageComponentsMutation() {
    const { props } = this;
    let self = this,
      { packages } = this.state,
      filteredInput = [];

    const { labbookName, owner } = store.getState().routes,
          { environmentId } = props;

    packages = packages.map((pkg) => {
      pkg.validity = 'checking';
      filteredInput.push({
        manager: pkg.manager,
        package: pkg.package,
        version: pkg.version,
      });
      return pkg;
    }).slice();

    this.setState({
      packages,
      disableInstall: true,
      installDependenciesButtonState: 'loading',
    });

    setBuildingState(true);
    props.setLookingUpPackagesState(true);

    PackageLookup.query(labbookName, owner, filteredInput).then((response) => {
      props.setLookingUpPackagesState(false);
      if (response.errors) {
        packages = packages.map((pkg) => {
          pkg.validity = 'valid';
          return pkg;
        });
        this.setState({ disableInstall: false, installDependenciesButtonState: 'error', packages });
        setTimeout(() => {
          self.setState({ installDependenciesButtonState: '' });
        }, 2000);
        props.setErrorMessage('Error occured looking up packages', response.errors);

        setBuildingState(false);
      } else {
        let resPackages = response.data.labbook.packages;
        let invalidCount = 0;
        let lastInvalid = null;
        resPackages = resPackages.map((pkg) => {
          if (pkg.isValid) {
            pkg.validity = 'valid';
          } else {
            pkg.validity = 'invalid';
            invalidCount++;
            lastInvalid = { package: pkg.package, manager: pkg.manager };
          }
          return pkg;
        });
        this.setState({ packages: resPackages });

        if (invalidCount) {
          const message = invalidCount === 1 ? `Unable to find package '${lastInvalid.package}'.` : `Unable to find ${invalidCount} packages.`;

          props.setErrorMessage('Packages could not be installed', [{ message }]);

          setBuildingState(false);
          this.setState({
            disableInstall: false,
            installDependenciesButtonState: '',
          });
        } else {
          filteredInput = [];
          const flatPackages = [],
                versionReference = {},
                existingPackages = props.environment.packageDependencies;

          resPackages.forEach((pkg) => {
            flatPackages.push(pkg.package);
          });

          const duplicates = existingPackages.edges.reduce((filtered, option) => {
            if (flatPackages.indexOf(option.node.package) > -1) {
              filtered.push(option.node.id);
              versionReference[option.node.package] = option.node.version;
            }

            return filtered;
          }, []);

          resPackages = resPackages.forEach((pkg) => {
            versionReference[pkg.package] !== pkg.version ? filteredInput.push({ package: pkg.package, manager: pkg.manager, version: pkg.version }) : duplicates.splice(duplicates.indexOf(pkg.id), 1);
            flatPackages.push(pkg.package);
          });

          if (filteredInput.length) {
            AddPackageComponentsMutation(
              labbookName,
              owner,
              filteredInput,
              1,
              environmentId,
              'PackageDependencies_packageDependencies',
              duplicates,
              (response, error) => {
                if (error) {
                  self.setState({
                    disableInstall: false,
                    installDependenciesButtonState: 'error',
                  });

                  setTimeout(() => {
                    self.setState({ installDependenciesButtonState: '' });
                  }, 2000);

                  props.setErrorMessage('Error adding packages.', error);
                } else {
                  self.setState({
                    disableInstall: false,
                    packages: [],
                    installDependenciesButtonState: 'finished',
                  });
                  props.fetchPackageVersion();
                  setTimeout(() => {
                    self.setState({ installDependenciesButtonState: '' });
                  }, 2000);
                }
              },
            );
          } else {
            this.props.setWarningMessage('All packages attempted to be installed already exist.');
            setBuildingState(false);
            self.setState({
              disableInstall: false,
              packages: [],
              installDependenciesButtonState: 'error',
            });
            setTimeout(() => {
              self.setState({ installDependenciesButtonState: '' });
            }, 2000);
          }
        }
      }
    });
  }

  /**
  *  @param {evt}
  *  remove dependency from list
  */
  _setSearchValue(evt) {
    this.setState({ searchValue: evt.target.value });
  }
  /** *
  *  @param {evt}
  *  get tabs data
  * */
  _getPackmanagerTabs() {
    const tabs = this.props.base && this.props.base.packageManagers.map((packageName) => {
      let count = 0;
      this.props.environment.packageDependencies.edges.forEach((edge) => {
        if (packageName === edge.node.manager) {
          count++;
        }
      });
      return { tabName: packageName, count };
    });
    return tabs;
  }
  /** *
  *  @param {String, String} pkg manager
  *  adds to removalpackages state pending removal of packages
  * */
  _addRemovalPackage(node) {
    const { manager, id, version } = node,
          pkg = node.package,
          newRemovalPackages = Object.assign({}, this.state.removalPackages),
          newUpdatePackages = Object.assign({}, this.state.updatePackages),
          updateAvailable = node.latestVersion && (node.version !== node.latestVersion);

    if (newRemovalPackages[manager]) {
      const index = Object.keys(newRemovalPackages[manager]).indexOf(pkg);

      if (index > -1) {
        delete newRemovalPackages[manager][pkg];
      } else {
        newRemovalPackages[manager][pkg] = id;
      }
    } else {
      newRemovalPackages[manager] = { [pkg]: id };
    }

    if (!node.version) {
      if (updateCheck[manager]) {
        updateCheck[manager][pkg] = { id, oldVersion: node.version };
      } else {
        updateCheck[manager] = { [pkg]: { id, oldVersion: node.version } };
      }
    }

    if (updateAvailable) {
      if (newUpdatePackages[manager]) {
        const index = Object.keys(newUpdatePackages[manager]).indexOf(pkg);

        if (index > -1) {
          delete newUpdatePackages[manager][pkg];
        } else {
          newUpdatePackages[manager][pkg] = { id, version: node.latestVersion };
        }
      } else {
        newUpdatePackages[manager] = { [pkg]: { id, version: node.latestVersion } };
      }
    }
    this.setState({ removalPackages: newRemovalPackages, updatePackages: newUpdatePackages });
  }

  /** *
  *  @param {}
  *  processes update packages and attempts to update
  * */
  @boundMethod
  _updatePackages() {
    const { status } = store.getState().containerStatus;
    const canEditEnvironment = config.containerStatus.canEditEnvironment(status) && !this.props.isLocked;
    const self = this;

    if (navigator.onLine) {
      if (canEditEnvironment) {
        const { labbookName, owner } = store.getState().routes;
        const { environmentId } = this.props;
        const filteredInput = [];
        const duplicates = [];

        Object.keys(this.state.updatePackages).forEach((manager) => {
          Object.keys(this.state.updatePackages[manager]).forEach((pkg) => {
            filteredInput.push({ manager, package: pkg, version: this.state.updatePackages[manager][pkg].version });
            duplicates.push(this.state.updatePackages[manager][pkg].id);
          });
        });

        AddPackageComponentsMutation(
          labbookName,
          owner,
          filteredInput,
          1,
          environmentId,
          'PackageDependencies_packageDependencies',
          duplicates,
          (response, error) => {
            this.setState({ removalPackages: {}, updatePackages: {} });
            if (error) {
              this.setState({ disableInstall: false, installDependenciesButtonState: 'error' });
              setTimeout(() => {
                self.setState({ installDependenciesButtonState: '' });
              }, 2000);
              this.props.setErrorMessage('Error adding packages.', error);
            } else {
              self.props.buildCallback(true);
              self.setState({
                disableInstall: false,
                packages: [],
                installDependenciesButtonState: 'finished',
              });
              setTimeout(() => {
                self.setState({ installDependenciesButtonState: '' });
              }, 2000);
            }
          },
        );
      } else {
        this._promptUserToCloseContainer();
      }
    } else {
      this.props.setErrorMessage('Cannot remove package at this time.', [{ message: 'An internet connection is required to modify the environment.' }]);
    }
  }

  /**
  *  @param {Object}
  *  hides packagemanager modal
  */
  _filterPackageDependencies(packageDependencies) {
    const { props, state } = this,
          searchValue = state.searchValue && state.searchValue.toLowerCase();

    const packages = state.latestVersionPackages.filter((node) => {
      const name = node && node.package ? node.package.toLowerCase() : '',
            searchMatch = ((searchValue === '') || (name.indexOf(searchValue) > -1));
      return (searchMatch && (node.manager === state.selectedTab));
    });

    return packages;
  }

  render() {
    const { props, state } = this,
          { packageDependencies } = props.environment,
          packageManagersTabs = this._getPackmanagerTabs(),
          noRemovalPackages = ((!state.removalPackages[state.selectedTab]) || (state.removalPackages[state.selectedTab] && !Object.keys(state.removalPackages[state.selectedTab]).length)),
          updateButtonAvailable = state.removalPackages[state.selectedTab] && state.updatePackages[state.selectedTab] && Object.keys(state.removalPackages[state.selectedTab]).length === Object.keys(state.updatePackages[state.selectedTab]).length,
          removeButtonCSS = classNames({
            'PackageDependencies__remove-button--full': !updateButtonAvailable,
            'PackageDependencies__remove-button--half': updateButtonAvailable,
          });

    if (state.latestVersionPackages) {
      const filteredPackageDependencies = this._filterPackageDependencies(state.latestVersionPackages);
      const packageMenu = classNames({
        PackageDependencies__menu: true,
        'PackageDependencies__menu--min-height': !props.packageMenuVisible,
      });
      const packagesProcessing = state.packages.filter(packageItem => packageItem.validity === 'checking');

      const addPackageCSS = classNames({
        PackageDependencies__btn: true,
        'PackageDependencies__btn--line-18': true,
        'PackageDependencies__btn--open': props.packageMenuVisible,
      });

      const addPackageContainer = classNames({
        PackageDependencies__addPackage: true,
        'Tooltip-data': props.isLocked,
      });

      const tooltipCSS = classNames({
        'Tooltip-data': props.isLocked,
      });

      const disableInstall = state.disableInstall || ((state.packages.length === 0) || (packagesProcessing.length > 0));

      return (
        <div className="PackageDependencies grid">
          <div className="PackageDependencies__card Card Card--auto Card--no-hover column-1-span-12">
            <div className="PackageDependencies__tabs">
              <ul className="tabs-list">
                {
                packageManagersTabs.map((tab, index) => {
                  const packageTab = classNames({
                    'PackageDependencies__tab tab': true,
                    'PackageDependencies__tab--selected tab-selected': (state.selectedTab === tab.tabName),
                  });

                  return (<li
                    key={tab + index}
                    className={packageTab}
                    onClick={() => this._setSelectedTab(tab.tabName, state.selectedTab === tab.tabName)}>
                    {`${tab.tabName} (${tab.count})`}
                  </li>);
                })
              }
              </ul>

            </div>
            <div
              className={addPackageContainer}
              data-tooltip="Container must be turned off to add packages.">

              <button
                disabled={props.isLocked}
                data-container-popup={true}
                onClick={() => this._toggleAddPackageMenu()}
                className={addPackageCSS}>
                Add Packages
              </button>

              <div className={packageMenu}>
                <div className="PackageDependencies__packageMenu">
                  <input
                    ref={el => this.inputPackageName = el}
                    disabled={packagesProcessing.length > 0}
                    className="PackageDependencies__input"
                    placeholder="Enter Dependency Name"
                    type="text"
                    onKeyUp={evt => this._updatePackageName(evt)}
                  />
                  <input
                    ref={el => this.inputVersion = el}
                    className="PackageDependencies__input--version"
                    placeholder="Version (Optional)"
                    disabled={state.selectedTab === 'apt' || (packagesProcessing.length > 0)}
                    type="text"
                    onKeyUp={evt => this._updateVersion(evt)}
                  />
                  <button
                    disabled={(this.state.packageName.length === 0)}
                    onClick={() => this._addStatePackage()}
                    className="PackageDependencies__btn--margin PackageDependencies__btn--round PackageDependencies__btn--add"
                  />
                </div>

                <div className="PackageDependencies__table--border">
                  <table>
                    <tbody>
                      {
                        state.packages.map((node, index) => {
                          const version = node.version === '' ? 'latest' : `${node.version}`;
                          const versionText = `${version === 'latest' ? node.validity === 'checking' ? 'retrieving latest version' : 'latest version' : `${version}`}`;
                          return (
                            <tr
                              className={`PackageDependencies__table-row PackageDependencies__table-row--${node.validity} flex`}
                              key={node.package + node.version}>
                              <td className="PackageDependencies__td--package">{`${node.package}`}</td>
                              <td className="PackageDependencies__td--version">
                              {versionText}
                                {
                                node.validity === 'checking' &&
                                <div className="PackageDependencies__versionLoading" />
                              }

                              </td>
                              <td className="PackageDependencies__table--no-right-padding" width="30">
                                {
                                !disableInstall &&
                                <button
                                  className="PackageDependencies__btn--round PackageDependencies__btn--remove--adder"
                                  onClick={() => this._removeStatePackages(node, index)}
                                />
                              }
                              </td>
                            </tr>);
                        })
                      }
                    </tbody>
                  </table>

                  <ButtonLoader
                    buttonState={this.state.installDependenciesButtonState}
                    buttonText="Install Selected Packages"
                    className="PackageDependencies__btn--absolute"
                    params={{}}
                    buttonDisabled={disableInstall}
                    clicked={this._addPackageComponentsMutation}
                  />

                </div>
              </div>
            </div>
            <div className="PackageDependencies__table-container">

              <table className="PackageDependencies__table">
                <thead>
                  <tr>
                    <th className="PackageDependencies__th">Package Name</th>
                    <th className="PackageDependencies__th">Current</th>
                    <th className="PackageDependencies__th">Latest</th>
                    <th className="PackageDependencies__th">Installed By</th>
                    {
                    noRemovalPackages ?
                      <th className="PackageDependencies__th--last">
                      Select
                      </th>
                    :
                      <th className="PackageDependencies__th--remove">
                        <div
                          data-tooltip="Container must be turned off to remove packages or update packages"
                          className={tooltipCSS}>
                          {
                          updateButtonAvailable &&
                            <button
                              disabled={props.isLocked}
                              className="PackageDependencies__update-button"
                              onClick={() => this._updatePackages()}>
                              Update
                            </button>
                        }
                          <button
                            disabled={props.isLocked}
                            className={removeButtonCSS}
                            onClick={() => this._removePackage()}>
                            Delete
                          </button>

                        </div>
                      </th>
                  }
                  </tr>
                </thead>
                <tbody>
                  {
                    filteredPackageDependencies.map((node, index) => (this._packageRow(node, index)))
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>);
    }
    return (<Loader />);
  }

  _packageRow(node, index) {
    const installer = node.fromBase ? 'System' : 'User',
      { version, latestVersion } = node,
      versionText = version || '',
      isSelected = this.state.removalPackages[node.manager] && Object.keys(this.state.removalPackages[node.manager]).indexOf(node.package) > -1,
      updateAvailable = node.version !== node.latestVersion,
      buttonCSS = classNames({
        'PackageDependencies__btn--round PackageDependencies__btn--remove': !isSelected,
        'PackageDependencies__btn--round PackageDependencies__btn--remove--selected': isSelected,
      }),
      tableRowCSS = classNames({
        'PackageDependencies__cell--optimistic-updating': node.id === undefined,
      });

    return (
      <tr
        className={tableRowCSS}
        key={node.package + node.manager + index}>
        <td>{node.package}</td>

        <td>
          {node.version}
        </td>

        <td className="PackageDependencies__cell--latest-column">

          <span>
            {node.latestVersion}
          </span>
          {
            node.latestVersion && (node.latestVersion !== node.version) && !node.fromBase &&
            <div className="PackageDependencies__updateAvailable" />
          }
        </td>

        <td>{installer}</td>

        <td width="60" className="PackageDependencies__cell--select">

          <button
            className={buttonCSS}
            disabled={node.fromBase || (node.id === undefined)}
            onClick={() => this._addRemovalPackage(node)}
          />
        </td>
      </tr>);
  }
}

const mapStateToProps = (state, ownProps) => state.packageDependencies;

const mapDispatchToProps = dispatch => ({
  setPackageMenuVisible,
  setErrorMessage,
  setContainerMenuWarningMessage,
  setBuildingState,
  setWarningMessage,
  setLookingUpPackagesState,
});

const PackageDependenciesContainer = connect(mapStateToProps, mapDispatchToProps)(PackageDependencies);


export default createPaginationContainer(
  PackageDependenciesContainer,
  {
    environment: graphql`fragment PackageDependencies_environment on Environment {
    packageDependencies(first: $first, after: $cursor) @connection(key: "PackageDependencies_packageDependencies", filters: []){
        edges{
          node{
            id
            schema
            manager
            package
            version
            latestVersion @include(if: $hasNext)
            fromBase
          }
          cursor
        }
        pageInfo{
          hasNextPage
          hasPreviousPage
          startCursor
          endCursor
        }
      }
    }`,
  },
  {
    direction: 'forward',
    getConnectionFromProps(props) {
      return props.environment && props.environment.packageDependencies;
    },
    getFragmentVariables(prevVars, first) {
      return {
        ...prevVars,
        first,
      };
    },
    getVariables(props, { count }, fragmentVariables) {
      const length = props.environment.packageDependencies.edges.length;
      const { labbookName } = store.getState().routes;

      const cursor = props.environment.packageDependencies.edges[length - 1].cursor;
      const hasNext = !props.environment.packageDependencies.pageInfo.hasNextPage;
      let first = count;

      return {
        first,
        cursor,
        name: labbookName,
        owner,
        hasNext,
        // in most cases, for variables other than connection filters like
        // `first`, `after`, etc. you may want to use the previous values.
        // orderBy: fragmentVariables.orderBy,
      };
    },
    query: graphql`
    query PackageDependenciesPaginationQuery($name: String!, $owner: String!, $first: Int!, $cursor: String, $hasNext: Boolean!){
     labbook(name: $name, owner: $owner){
       environment{
         ...PackageDependencies_environment
       }
     }
   }`,
  },
);
