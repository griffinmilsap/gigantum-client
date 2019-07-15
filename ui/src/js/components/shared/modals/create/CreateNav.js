import React, { PureComponent } from 'react';
import classNames from 'classnames';
// components
import ButtonLoader from 'Components/common/ButtonLoader';

type Props = {
  parentState: {},
  setComponent: () => {},
  hideModal: () => {},
  continueSave: () => {},
  isDataset: boolean,
  continueDisabled: boolean,
  createLabbookButtonState: string,
  selectedComponentId: string,
}

/**
  Gets text for the button loader bassed on isDataset and current selectedComponentId
  @param {Boolean} isDataset
  @param {Boolean} selectedComponentId
  @returns {String}
*/
const continueButtonText = (isDataset, selectedComponentId) => {
  let text = '';
  if (isDataset) {
    if ((selectedComponentId === 'createLabbook')) {
      text = 'Create Dataset';
    } else if (selectedComponentId === 'selectBase') {
      text = 'Create Dataset';
    }
  } else if (!isDataset) {
    if (selectedComponentId === 'createLabbook') {
      text = 'Continue';
    } else if (selectedComponentId === 'selectBase') {
      text = 'Create Project';
    }
  }
  return text;
};


/**
  @class CreateNav
  Pure Component that renders the buttons for the navigation menu
*/
class CreateNav extends PureComponent<Props> {
  props: Props;

  render() {
    const {
      setComponent,
      hideModal,
      continueSave,
      isDataset,
      continueDisabled,
      createLabbookButtonState,
      selectedComponentId,
    } = this.props;
    const buttonText = continueButtonText(isDataset, selectedComponentId);
    // declare css here
    const backButton = classNames({
      'CreateModal__progress-button': true,
      'Btn--flat Btn--width-80': true,
      hidden: (selectedComponentId === 'createLabbook'),
    });
    const createModalNav = classNames({
      CreateModal__actions: true,
    });

    return (
      <div className={createModalNav}>
        <div className="CreateModal__buttons">
          <button
            type="button"
            onClick={() => { setComponent('createLabbook'); }}
            className={backButton}
          >
            Back
          </button>

          <button
            type="button"
            onClick={() => { hideModal(); }}
            className="Btn--flat Btn--width-80"
          >
            Cancel
          </button>

          <ButtonLoader
            buttonState={createLabbookButtonState}
            buttonText={buttonText}
            className="Btn--last"
            params={{
              isSkip: false,
              text: 'Create Project',
            }}
            buttonDisabled={continueDisabled}
            clicked={continueSave}
          />
        </div>
      </div>
    );
  }
}

export default CreateNav;
