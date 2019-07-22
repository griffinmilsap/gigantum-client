import * as types from 'JS/redux/constants/constants';


export default (
  state = {
    status: '',
    containerMenuOpen: false,
    containerMenuWarning: '',
    viewContainerVisible: false,
    detailMode: false,
    advancedVisible: false,
  },
  action,
) => {
  if (action.type === types.CLOSE_ENVIRONMENT_MENUS) {
    return {
      ...state,
      packageMenuVisible: false,
      viewContainerVisible: false,
    };
  }
  if (action.type === types.RESET_DETAIL_STORE) {
    return {
      ...state,
      detailMode: false,
    };
  }
  if (action.type === types.TOGGLE_ADVANCED_VISIBLE) {
    return {
      ...state,
      advancedVisible: action.payload.advancedVisible,
    };
  }
  if (action.type === types.CONTAINER_MENU_WARNING) {
    return {
      ...state,
      containerMenuWarning: action.payload.message,
    };
  }
  if (action.type === types.UPDATE_CONTAINER_MENU_VISIBILITY) {
    return {
      ...state,
      containerMenuOpen: action.payload.containerMenuOpen,
    };
  }

  return state;
};
