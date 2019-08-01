// @flow
import React, { PureComponent } from 'react';
import classNames from 'classnames';
import PropTypes from 'prop-types';

type Props = {
  category: PropTypes.String,
  expandedIndex: PropTypes.Number,
  filterCategories: PropTypes.Array,
  handleAddition: PropTypes.Func,
  index: PropTypes.Number,
  setExpandedIndex: PropTypes.Number,
  toggleTooltip: PropTypes.Func,
  tooltipShown: PropTypes.Boolean,
}


class Category extends PureComponent<Props> {
  props: Props;

  render() {
    const {
      category,
      expandedIndex,
      filterCategories,
      handleAddition,
      index,
      setExpandedIndex,
      toggleTooltip,
      tooltipShown,
    } = this.props;

    const expandedIndexToSet = (expandedIndex === index)
      ? null
      : index;
    // delcare css here
    const filterSecionCSS = classNames({
      'AdvancedSearch__filter-section': true,
      selected: (expandedIndex === index),
    });

    return (
      <div
        key={category}
        className="AdvancedSearch__filter-container"
      >
        <div
          className={filterSecionCSS}
          onClick={() => setExpandedIndex(expandedIndexToSet) }
          key={category}
          data-resetselectedfilter-id="AdvancedSearch__filter-section"
        >
          {category}
        </div>

        { (category === 'CUDA Version')
          && (
          <div
            className="AdvancedSearch__info"
            data-resetselectedfilter-id="AdvancedSearch__info"
            onClick={() => toggleTooltip(!tooltipShown)}
          >
            { tooltipShown
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

        { (expandedIndex === index)
          && (
            <ul className="AdvancedSearch__filter-list">
              {
                filterCategories[category].map(filter => (
                  <li
                    key={filter}
                    onClick={() => handleAddition({ id: filter, text: filter }, category)}
                  >
                    {filter}
                  </li>
                ))
                }
            </ul>
          )
         }
      </div>
    );
  }
}

export default Category;
