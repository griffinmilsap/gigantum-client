import React, { Component } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
import ReactTooltip from 'react-tooltip';
// store
import store from 'JS/redux/store';
// config
import config from 'JS/config';
// assets
import './Tooltip.scss';

class Tooltip extends Component {
  state = {
    toolTipExpanded: false,
    isVisible: store.getState().helper,
  };

  static getDerivedStateFromProps(props, state) {
    const { toolTipExpanded } = state;
    return {
      ...state,
      toolTipExpanded: props.isVisible ? toolTipExpanded : false,
    };
  }

  /**
    * @param {}
    * subscribe to store to update state
  */
  componentDidMount() {
    window.addEventListener('click', this._hideTooltip);
  }

  /**
    @param {} -
    unsubscribe from event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._hideTooltip);
  }

  /**
   *  @param {event} evt
   *  closes tooltip box when tooltip is open and the tooltip has not been clicked on
   *
  */
  _hideTooltip = (evt) => {
    const { props, state } = this;
    if (state.toolTipExpanded
       && (evt.target.className.indexOf(props.section) === -1)) {
      this.setState({ toolTipExpanded: false });
    }
  }

  render() {
    const { props, state } = this;
    const { section } = props;
    const place = (section === 'descriptionOverview') ? 'right' : null;
    const toolTipCSS = classNames({
      Tooltip: props.isVisible,
      hidden: !props.isVisible,
      [section]: true,
      isSticky: store.getState().labbook.isSticky,
    });
    const toggleCSS = classNames({
      Tooltip__toggle: true,
      [section]: true,
      'Tooltip__toggle--active': state.toolTipExpanded,
    });
    return (
      <div className={toolTipCSS}>
        <div
          className={toggleCSS}
          data-tip={config.getTooltipText(section)}
          data-for={`Tooltip--${section}`}
          data-event="click focus"
        >
          { !state.toolTipExpanded
            && (
            <div className="Tooltip__glow-container">
              <div className="Tooltip__glow-ring-outer">
                <div className="Tooltip__glow-ring-inner" />
              </div>
            </div>
            )
          }
        </div>
        <ReactTooltip
          id={`Tooltip--${section}`}
          globalEventOff="click"
          place={place}
        />

      </div>
    );
  }
}

const mapStateToProps = state => ({
  isVisible: state.helper.isVisible,
});

const mapDispatchToProps = dispatch => ({
});

export default connect(mapStateToProps, mapDispatchToProps)(Tooltip);
