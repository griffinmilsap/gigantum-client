// @flow
// vendor
import React, { Component } from 'react';
import { WithContext as ReactTags } from 'react-tag-input';
import classNames from 'classnames';
// mutations
import CreateUserNoteMutation from 'Mutations/activity/CreateUserNoteMutation';
import { setErrorMessage } from 'JS/redux/actions/footer';
// assets
import './UserNote.scss';

let simple;

type Props = {
  changeFullScreenState: Function,
  datasetId: string,
  editorFullscreen: Boolean,
  labbookId: string,
  name: string,
  owner: string,
  sectionType: string,
  toggleUserNote: Function,
}

class UserNote extends Component<Props> {
  state = {
    tags: [],
    userSummaryText: '',
    addNoteDisabled: true,
    unsubmittedTag: '',
  };

  /**
    @param {}
    after component mounts apply simplemde to the dom element id:markdown
  */
  componentDidMount() {
    const { changeFullScreenState } = this.props;

    import('simplemde').then((comp) => {
      if (document.getElementById('markDown')) {
        const Simple = comp.default;
        simple = new Simple({
          element: document.getElementById('markDown'),
          spellChecker: true,
        });
        const fullscreenButton = document.getElementsByClassName('fa-arrows-alt')[0];
        const sideBySideButton = document.getElementsByClassName('fa-columns')[0];

        if (fullscreenButton) {
          fullscreenButton.addEventListener('click', () => changeFullScreenState());
        }

        if (sideBySideButton) {
          sideBySideButton.addEventListener('click', () => changeFullScreenState(true));
        }
      }
    });
  }

  /**
    @param {}
    calls CreateUserNoteMutation adds note to activity feed
  */
  _addNote = () => {
    const { state } = this;
    const self = this;
    const tags = state.tags.map(tag => (tag.text));
    const {
      name,
      owner,
      sectionType,
      labbookId,
      datasetId,
      toggleUserNote,
    } = this.props;
    const {
      unsubmittedTag,
      userSummaryText,
    } = this.state;

    if (unsubmittedTag.length) {
      this._handleAddition({
        id: unsubmittedTag,
        text: unsubmittedTag,
      });
    }


    this.setState({
      addNoteDisabled: true,
      unsubmittedTag: '',
    });

    CreateUserNoteMutation(
      sectionType,
      name,
      userSummaryText,
      simple.value(),
      owner,
      [],
      tags,
      labbookId || datasetId,
      (response, error) => {
        toggleUserNote(false);
        self.setState({
          tags: [],
          userSummaryText: '',
          addNoteDisabled: false,
        });
        if (error) {
          setErrorMessage(owner, name, 'Unable to unlink dataset', error);
        }
      },
    );
  }

  /**
    @param {number} index
    removes tag from list
  */
   _handleDelete = (index) => {
     const { tags } = this.state;

     tags.splice(index, 1);

     this.setState({ tags });
   }

   /**
     @param {String} tag
     add tag to list
   */
   _handleAddition = (tag) => {
     const { tags } = this.state;
     tags.push(tag);
     this.setState({ tags, unsubmittedTag: '' });
   }

   /**
     @param {String} tag
     @param {Number} curPos
     @param {Number} newPos
     drags tag to new position.
   */
   _handleDrag = (tag, currPos, newPos) => {
     const { tags } = this.state;

     // mutate array
     tags.splice(currPos, 1);
     tags.splice(newPos, 0, tag);

     // re-render
     this.setState({ tags });
   }


   /**
     @param {String} unsubmittedTag
     sets unsubmittedTag to state
   */
   _updateUnsubmittedTag = (unsubmittedTag) => {
     this.setState({ unsubmittedTag });
   }

   /**
     @param {Object} event
     calls updates state for summary text
     and enables addNote button if > 0
   */
   _setUserSummaryText = (evt) => {
     const summaryText = evt.target.value;
     this.setState({
       userSummaryText: summaryText,
       addNoteDisabled: (summaryText.length === 0),
     });
   }


   render() {
     const { toggleUserNote, editorFullscreen } = this.props;
     const { addNoteDisabled, tags } = this.state;
     // declare css here
     const userNoteSummaryCSS = classNames({
       UserNote__summary: true,
       'UserNote__summary--fullscreen': editorFullscreen,
     });
     return (
       <div className="UserNote flex flex--column">

         <div
           role="presentation"
           className="UserNote__close close"
           onClick={() => toggleUserNote(false)}
         />

         <input
           type="text"
           placeholder="Add a summary title"
           onKeyUp={evt => this._setUserSummaryText(evt)}
           className="UserNote__title"
         />
         <div className={userNoteSummaryCSS}>
           <textarea
             ref={(ref) => { this.markdown = ref; }}
             id="markDown"
           />
         </div>

         <ReactTags
           id="TagsInput"
           tags={tags}
           handleInputChange={this._updateUnsubmittedTag}
           handleDelete={(index) => { this._handleDelete(index); }}
           handleAddition={(tag) => { this._handleAddition(tag); }}
           handleDrag={(tag, currPos, newPos) => { this._handleDrag(tag, currPos, newPos); }}
         />
         <div className="BtnContainer">
           <button
             type="submit"
             className="Btn Btn--flat"
             onClick={() => toggleUserNote(false)}
           >
             Cancel
           </button>
           <button
             type="submit"
             className="Btn Btn--last"
             disabled={addNoteDisabled}
             onClick={() => { this._addNote(); }}
           >
             Add Note
           </button>
         </div>
       </div>
     );
   }
}

export default UserNote;
