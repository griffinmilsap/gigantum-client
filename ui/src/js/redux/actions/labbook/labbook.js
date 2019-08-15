import dispatcher from 'JS/redux/dispatcher';
import * as types from 'JS/redux/constants/constants';


/**
 * actions
 */

export const setBuildingState = (owner, name, isBuilding) => dispatcher(
  types.IS_BUILDING,
  { owner, name, isBuilding },
);

export const setMergeMode = (branchesOpen, mergeFilter) => dispatcher(
  types.MERGE_MODE,
  {
    branchesOpen,
    mergeFilter,
  },
);

export const setSyncingState = isSyncing => dispatcher(
  types.IS_SYNCING,
  { isSyncing },
);

export const setPublishingState = (owner, name, isPublishing) => dispatcher(
  types.IS_PUBLISHING,
  { owner, name, isPublishing },
);

export const setExportingState = isExporting => dispatcher(
  types.IS_EXPORTING,
  { isExporting },
);

export const setModalVisible = modalVisible => dispatcher(
  types.MODAL_VISIBLE,
  { modalVisible },
);

export const setStickyDate = isSticky => dispatcher(
  types.UPDATE_STICKY_STATE,
  { isSticky },
);

export const setSidepanelVisible = sidePanelVisible => dispatcher(
  types.UPDATE_SIDEPANEL_VISIBLE,
  { sidePanelVisible },
);

export const updateTransitionState = (transitioningLabbook, newState) => dispatcher(
  types.UPDATE_TRANSITION_STATE,
  { transitionState: { [transitioningLabbook]: newState } },
);


export const setFileBrowserLock = isUploading => dispatcher(
  types.IS_UPLOADING,
  { isUploading },
);
