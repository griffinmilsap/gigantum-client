// vendor
import React, { Component } from 'react';
import queryString from 'querystring';
import classNames from 'classnames';
import { connect } from 'react-redux';
// components
import CreateModal from 'Components/shared/modals/create/CreateModal';
import Loader from 'Components/common/Loader';
import LocalDatasetsContainer, { LocalDatasets } from 'Components/dashboard/datasets/localDatasets/LocalDatasets';
import RemoteDatasets from 'Components/dashboard/datasets/remoteDatasets/RemoteDatasets';
import LoginPrompt from 'Components/shared/modals/LoginPrompt';
import Tooltip from 'Components/common/Tooltip';
import FilterByDropdown from 'Components/dashboard/shared/filters/FilterByDropdown';
import SortByDropdown from 'Components/dashboard/shared/filters/SortByDropdown';
// utils
import Validation from 'JS/utils/Validation';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// config
import config from 'JS/config';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
import { setFilterText } from 'JS/redux/actions/datasetListing/datasetListing';
// assets
import './Datasets.scss';

class Datasets extends Component {
  constructor(props) {
    super(props);

    const {
      filter,
      orderBy,
      sort,
    } = queryString.parse(props.history.location.hash.slice(1));

    let { section } = this.props;
    if ((section !== 'cloud') && (section !== 'local')) {
      section = 'local';
    }

    this.state = {
      datasetModalVisible: false,
      oldDatasetName: '',
      newDatasetName: '',
      renameError: '',
      showNamingError: false,
      filter: filter || 'all',
      sortMenuOpen: false,
      refetchLoading: false,
      selectedSection: section,
      showLoginPrompt: false,
      orderBy: orderBy || 'modified_on',
      sort: sort || 'desc',
      filterMenuOpen: false,
    };
  }

  /**
    * @param {}
    * subscribe to store to update state
    * set unsubcribe for store
  */
  componentDidMount() {
    document.title = 'Gigantum';

    window.addEventListener('click', this._closeSortMenu);
    window.addEventListener('click', this._closeFilterMenu);
    window.addEventListener('scroll', this._captureScroll);
    window.addEventListener('click', this._hideSearchClear);
  }

  /**
    * @param {}
    * fires when component unmounts
    * removes added event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._closeSortMenu);
    window.removeEventListener('click', this._closeFilterMenu);
    window.removeEventListener('scroll', this._captureScroll);
    window.removeEventListener('click', this._hideSearchClear);
  }

  UNSAFE_componentWillReceiveProps(nextProps) {
    const paths = nextProps.history.location.pathname.split('/');
    const sectionRoute = paths.length > 2 ? paths[2] : 'local';

    this.setState({ selectedSection: sectionRoute });
  }

  /**
    * @param {}
    * fires when user identity returns invalid session
    * prompts user to revalidate their session
  */
  _closeLoginPromptModal = () => {
    this.setState({
      showLoginPrompt: false,
    });
  }

  /**
    * @param {event} evt
    * fires when sort menu is open and the user clicks elsewhere
    * hides the sort menu dropdown from the view
  */
  _closeSortMenu = (evt) => {
    const { state } = this;
    const isSortMenu = evt && evt.target && evt.target.className && (evt.target.className.indexOf('Dropdown__sort-selector') > -1);

    if (!isSortMenu && state.sortMenuOpen) {
      this.setState({ sortMenuOpen: false });
    }
  }

  /**
    * @param {event} evt
    * fires when filter menu is open and the user clicks elsewhere
    * hides the filter menu dropdown from the view
  */
  _closeFilterMenu = (evt) => {
    const { state } = this;
    const isFilterMenu = evt.target.className.indexOf('Dropdown__filter-selector') > -1;

    if (!isFilterMenu && state.filterMenuOpen) {
      this.setState({ filterMenuOpen: false });
    }
  }

  /**
    * @param {}
    * fires on window clock
    * hides search cancel button when clicked off
  */
  _hideSearchClear = (evt) => {
    const { state } = this;
    if (state.showSearchCancel
      && (evt.target.className !== 'Datasets__search-cancel')
      && (evt.target.className !== 'Datasets__search no--margin')) {
      this.setState({ showSearchCancel: false });
    }
  }

  /**
    *  @param {string} datasetName - inputs a dataset name
    *  routes to that dataset
  */
  _goToDataset = (datasetName, owner) => {
    this.setState({ datasetName, owner });
  }

  /**
    *  @param {string} datasetName
    *  closes dataset modal and resets state to initial state
    */
  _closeDataset = (datasetName) => {
    this.setState({
      datasetModalVisible: false,
      oldDatasetName: '',
      newDatasetName: '',
      showNamingError: false,
    });
  }

  /**
  *  @param {event} evt
  *  sets new dataset title to state
  */
  _setDatasetTitle = (evt) => {
    const isValid = Validation.datasetName(evt.target.value);
    if (isValid) {
      this.setState({
        newDatasetName: evt.target.value,
        showNamingError: false,
      });
    } else {
      this.setState({ showNamingError: true });
    }
  }

  /**
  * @param {string} filter
  sets state updates filter
  */
  _setFilter = (filter) => {
    this.setState({ filterMenuOpen: false, filter });
    this._changeSearchParam({ filter });
  }

  /**
   sets state for filter menu
   */
  _toggleFilterMenu = () => {
    const { state } = this;
    this.setState({ filterMenuOpen: !state.filterMenuOpen });
  }

  /**
  sets state for sort menu
  */
  _toggleSortMenu = () => {
    const { state } = this;
    this.setState({ sortMenuOpen: !state.sortMenuOpen });
  }

  /**
  * @param {string} section
  replaces history and checks session
  */
  _setSection = (section) => {
    const { props } = this;
    if (section === 'cloud') {
      this._viewRemote();
    } else {
      props.history.replace(`../datasets/${section}${props.history.location.search}`);
    }
  }

  /**
  * @param {object} dataset
  * returns true if dataset's name or description exists in filtervalue, else returns false
  */
  _filterSearch = (dataset) => {
    const { props } = this;
    const hasNoFileText = (props.filterText === '');
    const nameMatches = dataset.node
      && dataset.node.name
      && (dataset.node.name.toLowerCase().indexOf(props.filterText.toLowerCase()) > -1);
    const descriptionMatches = dataset.node
      && dataset.node.description
      && (dataset.node.description.toLowerCase().indexOf(props.filterText.toLowerCase()) > -1);

    if (hasNoFileText
      || nameMatches
      || descriptionMatches) {
      return true;
    }
    return false;
  }

  /**
   * @param {Object} datasetList
   * @param {String} filter
   * @param {Boolean} isLoading
   * @return {array} filteredDatasets
  */
  _filterDatasets = (datasetList, filter, isLoading) => {
    const { state } = this;
    if (isLoading) {
      return [];
    }
    const datasets = (state.selectedSection === 'local')
      ? datasetList.localDatasets.edges
      : datasetList.remoteDatasets.edges;
    const username = localStorage.getItem('username');
    const self = this;
    let filteredDatasets = [];

    if (filter === 'owner') {
      filteredDatasets = datasets.filter(
        dataset => ((dataset.node.owner === username)
        && self._filterSearch(dataset)),
      );
    } else if (filter === 'others') {
      filteredDatasets = datasets.filter(
        dataset => (dataset.node.owner !== username
          && self._filterSearch(dataset)),
      );
    } else {
      filteredDatasets = datasets.filter(dataset => self._filterSearch(dataset));
    }

    return filteredDatasets;
  }

  /**
    * @param {}
    * fires when handleSortFilter triggers refetch
    * references child components and triggers their refetch functions
  */
  _showModal = () => {
    // TODO remove refs this is deprecated
    this.createModal._showModal();
  }

  /**
    *  @param {string} selected
    * fires when setSortFilter validates user can sort
    * triggers a refetch with new sort parameters
  */
  _handleSortFilter = (orderBy, sort) => {
    const { props } = this;
    this.setState({ sortMenuOpen: false, orderBy, sort });
    this._changeSearchParam({ orderBy, sort });
    props.refetchSort(orderBy, sort);
  }

  /**
    *  @param {string, boolean} orderBy sort
    * fires when user selects a sort option
    * checks session and selectedSection state before handing off to handleSortFilter
  */
  _setSortFilter = (orderBy, sort) => {
    const { props, state } = this;
    if (state.selectedSection === 'remoteDatasets') {
      UserIdentity.getUserIdentity().then((response) => {
        if (navigator.onLine) {
          if (response.data) {
            if (response.data.userIdentity.isSessionValid) {
              this._handleSortFilter(orderBy, sort);
            } else {
              props.auth.renewToken(true, () => {
                if (!state.showLoginPrompt) {
                  this.setState({ showLoginPrompt: true });
                }
              }, () => {
                this._handleSortFilter(orderBy, sort);
              });
            }
          }
        } else if (!state.showLoginPrompt) {
          this.setState({ showLoginPrompt: true });
        }
      });
    } else {
      this._handleSortFilter(orderBy, sort);
    }
  }

  /**
    * @param {}
    * fires when user selects remote dataset view
    * checks user auth before changing selectedSection state
  */
  _viewRemote = () => {
    const { props, state } = this;
    UserIdentity.getUserIdentity().then((response) => {
      if (navigator.onLine) {
        if (response.data && response.data.userIdentity.isSessionValid) {
          props.history.replace(`../datasets/cloud${props.history.location.search}`);
          this.setState({ selectedSection: 'cloud' });
        } else {
          props.auth.renewToken(true, () => {
            if (!state.showLoginPrompt) {
              this.setState({ showLoginPrompt: true });
            }
          }, () => {
            props.history.replace(`../datasets/cloud${props.history.location.search}`);
            this.setState({ selectedSection: 'cloud' });
          });
        }
      } else if (!state.showLoginPrompt) {
        this.setState({ showLoginPrompt: true });
      }
    });
  }

  /**
  *  @param {evt}
  *  sets the filterValue in state
  */
  _setFilterValue = (evt) => {
    setFilterText(evt.target.value);
    // TODO remove refs this is deprecated
    if (this.datasetSearch.value !== evt.target.value) {
      this.datasetSearch.value = evt.target.value;
    }
  }

  /**
    *  @param {object} newValues
    *  changes the query params to new sort and filter values
  */
  _changeSearchParam = (newValues) => {
    const { props } = this;
    const searchObj = Object.assign(
      {},
      queryString.parse(props.history.location.hash.slice(1)),
      newValues,
    );
    props.history.replace(`..${props.history.location.pathname}#${queryString.stringify(searchObj)}`);
  }

  /**
    *  @param {} -
    *  forces state update ad sets to local view
  */
  _forceLocalView = () => {
    this.setState({
      selectedSection: 'local',
      showLoginPrompt: true,
    });
  }

  render() {
    const { props, state } = this;
    const datasetsCSS = classNames({
      Datasets: true,
      'Datasets--demo': (window.location.hostname === config.demoHostName) || props.diskLow,
    });

    if (props.datasetList !== null || props.loading) {
      const localNavItemCSS = classNames({
        Tab: true,
        'Tab--local': true,
        'Tab--selected': state.selectedSection === 'local',
      });
      const cloudNavItemCSS = classNames({
        Tab: true,
        'Tab--cloud': true,
        'Tab--selected': state.selectedSection === 'cloud',
      });

      return (

        <div className={datasetsCSS}>

          <CreateModal
            ref={(modal) => { this.createModal = modal; }}
            handler={this.handler}
            history={props.history}
            datasets
            {...props}
          />

          <div className="Datasets__panel-bar">
            <h6 className="Datasets__username">{localStorage.getItem('username')}</h6>
            <h1>Datasets</h1>

          </div>
          <div className="Datasets__menu  mui-container flex-0-0-auto">
            <ul className="Tabs">
              <li className={localNavItemCSS}>
                <a onClick={() => this._setSection('local')}>Local</a>
              </li>
              <li className={cloudNavItemCSS}>
                <a onClick={() => this._setSection('cloud')}>Gigantum Hub</a>
              </li>

              <Tooltip section="cloudLocal" />
            </ul>

          </div>
          <div className="Datasets__subheader grid">
            <div className="Datasets__search-container column-2-span-6 padding--0">
              <div className="Input Input--clear">
                { (props.filterText.length !== 0)
                    && (
                      <button
                        type="button"
                        className="Btn Btn--flat"
                        onClick={() => this._setFilterValue({ target: { value: '' } })}
                      >
                       Clear
                      </button>
                    )
                  }
                <input
                  type="text"
                  ref={(modal) => { this.datasetSearch = modal; }}
                  className="Datasets__search margin--0"
                  placeholder="Filter Datasets by name or description"
                  defaultValue={props.filterText}
                  onKeyUp={evt => this._setFilterValue(evt)}
                  onFocus={() => this.setState({ showSearchCancel: true })}
                />
              </div>
            </div>

            <FilterByDropdown
              {...this.state}
              type="Dataset"
              toggleFilterMenu={this._toggleFilterMenu}
              setFilter={this._setFilter}
            />
            <SortByDropdown
              {...this.state}
              toggleSortMenu={this._toggleSortMenu}
              setSortFilter={this._setSortFilter}
            />
          </div>
          { (!props.loading) && (state.selectedSection === 'local')
            && (
              <LocalDatasetsContainer
                datasetListId={props.datasetList.id}
                localDatasets={props.datasetList.datasetList}
                showModal={this._showModal}
                goToDataset={this._goToDataset}
                filterDatasets={this._filterDatasets}
                filterState={state.filter}
                setFilterValue={this._setFilterValue}
                changeRefetchState={bool => this.setState({ refetchLoading: bool })}
                {...props}
              />
            )
          }
          { (!props.loading) && (state.selectedSection === 'cloud')
            && (
              <RemoteDatasets
                datasetListId={props.datasetList.datasetList.id}
                remoteDatasets={props.datasetList.datasetList}
                showModal={this._showModal}
                goToLabbook={this._goToLabbook}
                filterDatasets={this._filterDatasets}
                filterState={state.filter}
                setFilterValue={this._setFilterValue}
                forceLocalView={() => { this._forceLocalView(); }}
                changeRefetchState={bool => this.setState({ refetchLoading: bool })}
                {...props}
              />
            )
          }
          { props.loading
            && (
              <LocalDatasets
                loading
                showModal={this._showModal}
                filterDatasets={this._filterDatasets}
                section={props.section}
                history={props.history}
              />
            )
          }
          {
            state.showLoginPrompt
            && <LoginPrompt closeModal={this._closeLoginPromptModal} />
          }
        </div>
      );
    } if (props.datasetList === null) {
      UserIdentity.getUserIdentity().then((response) => {
        if (response.data && response.data.userIdentity.isSessionValid) {
          setErrorMessage('Failed to fetch Datasets.', [{ message: 'There was an error while fetching Datasets. This likely means you have a corrupted Dataset directory.' }]);
          return (
            <div className="Datasets__fetch-error">
                There was an error attempting to fetch Datasets.
              <br />
                Try restarting Gigantum and refresh the page.
              <br />
                If the problem persists
              <a
                target="_blank"
                href="https://spectrum.chat/gigantum"
                rel="noopener noreferrer"
              >
                {' request assistance here.'}
              </a>
            </div>
          );
        }
        props.auth.login();
      });
    }

    return (<Loader />);
  }
}

const mapStateToProps = state => ({
  filterText: state.datasetListing.filterText,
});

const mapDispatchToProps = dispatch => ({
});

export default connect(mapStateToProps, mapDispatchToProps)(Datasets);
