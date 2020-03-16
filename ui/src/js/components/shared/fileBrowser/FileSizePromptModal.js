// @flow
import React, { PureComponent } from 'react';
// compontnents
import Modal from 'Components/common/Modal';
// assets
import './FileSizePromptModal.scss';

/**
*   @param {}
*  get warning and limit sizes
*/
const getSizes = (section) => {
  return {
    warning: (section === 'code') ? 'Warning: 10MB' : 'Warning: 100MB',
    limit: (section === 'code') ? 'Limit: 100MB' : 'Limit: 500MB',
  }
};

class FileSizePromptModal extends PureComponent {
  render() {
    const {
      cancelUpload,
      userRejectsUpload,
      userAcceptsUpload,
      uploadPromptText,
      filePrompted,
      fileTooLarge,
      section,
    } = this.props;
    const { warning, limit } = getSizes(section);

    return (
      <Modal
        handleClose={() => cancelUpload()}
        size="large"
        noPadding
        noPaddingModal
        renderContent={() => (
          <div className="FileSizePromptModal">
            <div className="FileSizePromptModal__header">
              <h4 className="FileSizePromptModal__header-text">Large File Warning</h4>
            </div>
            <div className="FileSizePromptModal__subheader flex justify--space-between">
              <div className="flex flex--column align-items--center justify--center">
                <div className="FileSizePromptModal__subheader-title">
                  {section}
                  &nbsp;File Size Limits
                </div>
                <ul>
                  <li>{warning}</li>
                  <li>{limit}</li>
                </ul>
              </div>
              <div className="FileSizePromptModal__subheader-text">
                File size limits are in place to maintain Project performance and
                stability, due to the limitations of Git and Git-lfs,
                which are used to version files in a Project.
              </div>
            </div>
            <div className="FileSizePromptModal__flex flex justify--center flex--column">

              <p className="FileSizePromptModal__upload-text align-self--center">{ uploadPromptText }</p>
              {
                (section === 'input')
                && (
                  <p className="FileSizePromptModal__tip-text align-self--center">
                    Tip: Try using a Dataset to manage large input files. Datasets support individual files up to 15GB without a large performance penalty, support downloading individual files, provide deduplication, and more.
                  </p>
                )
              }

            </div>

            <div className="FileSizePromptModal__buttonContainer flex justify--space-around">

              <button
                className="Btn--flat"
                onClick={() => cancelUpload()}
                type="button"
              >
                Cancel
              </button>
              <button
                onClick={() => userAcceptsUpload()}
                type="button"
                disabled={!filePrompted}
              >
                Continue
              </button>
            </div>
          </div>
        )
      }
      />
    );
  }
}

export default FileSizePromptModal;
