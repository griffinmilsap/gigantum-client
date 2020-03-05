// vendor
import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// components
import Tooltip from 'Components/common/Tooltip';
// mutations
import SetLabbookDescriptionMutation from 'Mutations/repository/description/SetLabbookDescriptionMutation';
import SetDatasetDescriptionMutation from 'Mutations/repository/description/SetDatasetDescriptionMutation';
// assets
import './Description.scss';


/**
* @param {string} description
* gets descrtiption and removes \n
* @return {string}
*/
const getDescription = (description) => {
  const descriptionText = description
    ? description.replace(/\n/g, ' ')
    : '';

  return descriptionText;
};

type Props = {
  description: string,
  dataset: {
    id: string,
  },
  hovered: boolean,
  labbook: {
    id: string,
  },
  name: string,
  owner: string,
  sectionType: string,
}

class Description extends Component<Props> {
  state = {
    editingDescription: false,
    descriptionEdited: false,
    descriptionText: getDescription(this.props.description),
    lastSavedDescription: getDescription(this.props.description),
    savingDescription: false,
    hovered: false,
    textareaWidth: '270px',
    textareaHeight: '66px',
  };

  static getDerivedStateFromProps(nextProps, state) {
    const descriptionText = state.descriptionEdited
      ? state.descriptionText
      : nextProps.description;
    return {
      ...state,
      descriptionText,
    };
  }

  /*
    adds event listeners
  */
  componentDidMount() {
    window.addEventListener('click', this._handleClick);
  }

  /*
    removes event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._handleClick);
  }

  /**
    *  @param {event} evt
    handles click outside description
  */
  _handleClick = (evt) => {
    const { editingDescription } = this.state;
    if (
      (evt.target.className.indexOf('Description') === -1)
      && editingDescription
    ) {
      this._cancelDescription();
    }
  }

  /**
   @param {String} owner
   @param {String} name
   calls mutation to save labbook description
   */
  _saveLabbookDescription = (owner, name) => {
    const { descriptionText } = this.state;
    const { sectionType } = this.props;
    const sectionId = this.props[sectionType].id;

    SetLabbookDescriptionMutation(
      owner,
      name,
      descriptionText,
      sectionId,
      (res, error) => {
        if (error) {
          console.log(error);
          setErrorMessage(owner, name, 'Description was not set: ', error);
        } else {
          this.setState({
            descriptionEdited: false,
            editingDescription: false,
            savingDescription: false,
            lastSavedDescription: descriptionText.replace(/\n/g, ' '),
          });
        }
      },
    );
  }

  /**
   @param {String} owner
   @param {String} name
   calls mutation to save dataset description
   */
  _saveDatasetDescription = (owner, name) => {
    const { descriptionText } = this.state;
    const { sectionType } = this.props;
    const sectionId = this.props[sectionType].id;

    SetDatasetDescriptionMutation(
      owner,
      name,
      descriptionText,
      sectionId,
      (res, error) => {
        if (error) {
          console.log(error);
          setErrorMessage(owner, name, 'Description was not set: ', error);
        } else {
          this.setState({
            descriptionEdited: false,
            editingDescription: false,
            savingDescription: false,
            lastSavedDescription: descriptionText.replace(/\n/g, ' '),
          });
        }
      },
    );
  }

  /**
    *  @param {}
    *  fires setlabbookdescription mutation
  */
  _saveDescription = () => {
    const {
      owner,
      name,
      sectionType,
    } = this.props;

    this.setState({ savingDescription: true });

    if (sectionType === 'labbook') {
      this._saveLabbookDescription(owner, name);
    } else {
      this._saveDatasetDescription(owner, name);
    }
  }

  /**
    *  @param {}
    *  reverts description back to last save
  */
  _cancelDescription = () => {
    const { lastSavedDescription } = this.state;
    this.setState({
      descriptionEdited: false,
      editingDescription: false,
      descriptionText: lastSavedDescription,
    });
  }

  /**
    *  @param {}
    *  handles enabling description editing and sets textareaCSS
  */
  _editingDescription = () => {
    const { editingDescription } = this.state;
    if (!editingDescription) {
      const element = document.getElementsByClassName('Description__container')[0];
      const width = element.offsetWidth - 30;
      const height = element.offsetHeight - 4;
      this.setState({
        editingDescription: true,
        textareaWidth: `${width}px`,
        textareaHeight: `${height}px`,
      },
      () => {
        this.descriptionInput.focus();
      });
    }
  }

  /**
    *  @param {}
    *  handles enabling description editing and sets textareaCSS
  */
  _updateDescrtipionText = (evt) => {
    this.setState({
      descriptionText: evt.target.value.replace(/\n/g, ' '),
      descriptionEdited: true,
    });
  }

  /**
    *  @param {}
    *  handles enabling description editing and sets textareaCSS
  */
  _textareaKeyDown = (evt) => {
    if (evt.key === 'Enter') {
      this.setState({ editingDescription: false });
      this._saveDescription();
    }
  }

  render() {
    const stateHovered = this.state.hovered;
    const {
      hovered,
    } = this.props;
    const {
      editingDescription,
      descriptionText,
      textareaHeight,
    } = this.state;
    const displayedText = descriptionText && descriptionText.length
      ? descriptionText
      : 'Add description...';
    const defaultText = descriptionText || '';
    // declare css here
    const descriptionCSS = classNames({
      Description__text: true,
      empty: !descriptionText,
    });
    const descriptionContainerCSS = classNames({
      Description__container: true,
      'Description__container--hovered': stateHovered && !editingDescription,
      'visibility-hidden': hovered,
    });

    return (
      <div className="Description">
        <div
          className={descriptionContainerCSS}
          onMouseEnter={() => this.setState({ hovered: true })}
          onMouseLeave={() => this.setState({ hovered: false })}
          onClick={() => this._editingDescription()}
          role="presentation"
        >

          { editingDescription
            ? (
              <Fragment>
                <textarea
                  ref={(input) => { this.descriptionInput = input; }}
                  maxLength="80"
                  className="Description__input"
                  type="text"
                  onChange={(evt) => { this._updateDescrtipionText(evt); }}
                  onKeyDown={(evt) => { this._textareaKeyDown(evt); }}
                  placeholder="Short description of Project"
                  defaultValue={defaultText}
                />
                <div
                  className="Description__input-buttons"
                  style={{ height: textareaHeight }}
                >
                  <button
                    onClick={this._cancelDescription}
                    className="Description__input-cancel Btn Btn--noMargin"
                    type="button"
                  />
                  <button
                    onClick={this._saveDescription}
                    className="Description__input-save Btn Btn--noMargin"
                    type="button"
                  />
                </div>
              </Fragment>
            )
            : (
              <p className={descriptionCSS}>
                <span className="Description__text">{displayedText}</span>
                { stateHovered
                    && (
                      <button
                        className="Btn Btn__edit Btn__edit--DescriptionPosition Btn--medium Btn--noShadow absolute Btn--noMargin"
                        type="button"
                      />
                    )
                  }
              </p>
            )}
        </div>
        <Tooltip section="descriptionOverview" />
      </div>
    );
  }
}

export default Description;
