// vendor
import uuidv4 from 'uuid/v4';
// constants
import * as types from 'JS/redux/constants/constants';


export default (
  state = {
    isSticky: false,
    isProcessing: false,
    isUploading: false,
    isSyncing: false,
    isExporting: false,
  },
  action,
) => {
  if (action.payload && action.payload.labbookName) {
    const { owner, labbookName } = action.payload;
    const namespace = `${owner}_${labbookName}`;
    const namespaceExist = state[namespace];

    if (namespaceExist === undefined) {
      // preventing detail mode from opening until feature has been fully implemented
      return {
        [namespace]: {
          ...state,
        },
        ...state,
        labbookName,
        owner,
        forceUpdate: uuidv4(),
      };
    }
  }
  if (action.type === types.UPDATE_STICKY_STATE) {
    const { namespace, isSticky } = action.payload;
    // preventing detail mode from opening until feature has been fully implemented
    return {
      ...state,
      [namespace]: {
        ...state[namespace],
        isSticky,
        forceUpdate: uuidv4(),
      },
    };
  } if (action.type === types.IS_UPLOADING) {
    const { namespace, isUploading } = action.payload;
    return {
      ...state,
      [namespace]: {
        ...state[namespace],
        isUploading,
        forceUpdate: uuidv4(),
      },
      isUploading,
    };
  } if (action.type === types.SET_IS_PROCESSING) {
    const { namespace, isProcessing } = action.payload;
    return {
      ...state,
      [namespace]: {
        ...state[namespace],
        isProcessing,
        forceUpdate: uuidv4(),
      },
    };
  }
  if (action.type === types.IS_SYNCING) {
    const { namespace, isSyncing } = action.payload;
    return {
      ...state,
      [namespace]: {
        ...state[namespace],
        isSyncing,
        forceUpdate: uuidv4(),
      },
    };
  }
  if (action.type === types.IS_EXPORTING) {
    const { namespace, isExporting } = action.payload;
    return {
      ...state,
      [namespace]: {
        ...state[namespace],
        isExporting,
        forceUpdate: uuidv4(),
      },
    };
  }

  return state;
};
