// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { WithContext, WithOutContext } from 'react-tag-input';
// assets
import './AdvancedSearch.scss';

export default class AdvancedSearch extends Component {
  constructor(props) {
    super(props);
    this.state = {
      expandedIndex: null,
      tooltipShown: false,
    };
    this._resetSelectedFilter = this._resetSelectedFilter.bind(this);
  }

  /**
     *  @param {}
     *  add event listeners
  */
  componentDidMount() {
    window.addEventListener('click', this._resetSelectedFilter);
  }

  /**
     *  @param {}
     *  cleanup event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._resetSelectedFilter);
  }

  /**
    @param {number} i
    removes tag from list
  */
  _handleDelete = (i) => {
    const { tags } = this.props;

    tags.splice(i, 1);

    this.props.setTags(tags);
  }

  /**
    @param {number} i
    add tag to list
  */
  _handleAddition = (tag, category) => {
    const { tags } = this.props;
    if (category) {
      tag.className = category;
    }
    tags.push(tag);

    this.props.setTags(tags);
  }

  /**
    @param {}
    add tag to list
  *  @calls {this._handleAddition}
  */
  _addTag = () => {
    const { value } = document.getElementById('AdvancedSearch');
    if (value.length) {
      const tag = {
        id: value,
        text: value,
      };
      this._handleAddition(tag);
    }
  }

  /**
   *  @param {event} evt
   *  resets expanded index state
   *
  */
  _resetSelectedFilter(evt) {
    if (evt.target.getAttribute('data-resetselectedfilter-id') !== 'AdvancedSearch__filter-section') {
      this.setState({ expandedIndex: null });
    }
    if (evt.target.getAttribute('data-resetselectedfilter-id') !== 'AdvancedSearch__info') {
      this.setState({ tooltipShown: false });
    }

    // ReactTags class comes from react-tag-input library
    if (evt.target.getAttribute('data-resetselectedfilter-id') !== 'AdvancedSearch'
    && evt.target.getAttribute('data-resetselectedfilter-id') !== 'AdvancedSearch__filter-section'
    && evt.target.className.indexOf('ReactTags') === -1) {
      this.setState({ focused: false });
    }
  }

  render() {
    const {
      tags,
      withoutContext,
      customStyle,
      autoHide,
      showButton,
      filterCategories,
    } = this.props;
    const { state } = this;
    const suggestions = [];
    const rawKeys = [];
    const TagComponent = withoutContext ? WithOutContext : WithContext;
    Object.keys(filterCategories).forEach((category) => {
      filterCategories[category].forEach((key) => {
        if (rawKeys.indexOf(key) === -1) {
          rawKeys.push(key);
          suggestions.push({ id: key, text: key, className: category });
        }
      });
    });

    const advancedSearchCSS = classNames({
      AdvancedSearch: true,
      'AdvancedSearch--packages': customStyle === 'packages',
      'AdvancedSearch--tagsExist': tags.length,
    });
    const filterCSS = classNames({
      AdvancedSearch__filters: true,
      'AdvancedSearch__filters--dropdown': autoHide,
      hidden: autoHide && !state.focused,
    });

    return (
      <div
        className={advancedSearchCSS}
      >
        <div className="flex">
          <div className="flex-1">
            <TagComponent
              id="AdvancedSearch"
              tags={tags}
              autocomplete
              autofocus={false}
              suggestions={suggestions}
              placeholder="Search by keyword, tags or filters"
              data-resetselectedfilter-id="AdvancedSearch"
              handleDelete={(index) => { this._handleDelete(index); }}
              handleAddition={(tag) => { this._handleAddition(tag); }}
              handleInputFocus={() => this.setState({ focused: true })}
            />
          </div>
          {
            showButton
            && (
              <button
                className="Btn Btn__AdvancedSearch"
                onClick={() => this._addTag()}
                type="button"
              />
            )
          }
        </div>
        <div className={filterCSS}>
          {
          Object.keys(this.props.filterCategories).map((category, index) => (
            <div
              key={category}
              className="AdvancedSearch__filter-container"
            >
              <div
                className={`AdvancedSearch__filter-section ${this.state.expandedIndex === index ? 'selected' : ''}`}
                onClick={() => this.setState({ expandedIndex: this.state.expandedIndex === index ? null : index })}
                key={category}
                data-resetselectedfilter-id="AdvancedSearch__filter-section"

              >
                {category}
              </div>
              {
              (category === 'CUDA Version')
              && (
              <div
                className="AdvancedSearch__info"
                data-resetselectedfilter-id="AdvancedSearch__info"
                onClick={() => this.setState({ tooltipShown: !this.state.tooltipShown })}
              >
                {
                  this.state.tooltipShown
                  && (
                  <div className="InfoTooltip">
                    CUDA enabled bases will automatically use the NVIDIA Container Runtime when NVIDIA drivers on the host are compatible with the CUDA version installed in the Base.&nbsp;&nbsp;
                    <a
                      target="_blank"
                      href="https://docs.gigantum.com/docs/using-cuda-with-nvidia-gpus"
                      rel="noopener noreferrer"
                    >
                      Learn more.
                    </a>
                  </div>
                  )
                }
              </div>
              )
            }

              {
                (this.state.expandedIndex === index)
                && (
                <ul className="AdvancedSearch__filter-list">
                  {
                        this.props.filterCategories[category].map(filter => (
                          <li
                            key={filter}
                            onClick={() => this._handleAddition({ id: filter, text: filter }, category)}
                          >
                            {filter}
                          </li>
                        ))
                    }
                </ul>
                )
            }
            </div>
          ))
        }
        </div>
      </div>
    );
  }
}
