import dispatcher from 'JS/redux/dispatcher';
import * as types from 'JS/redux/constants/constants';
/**
 * actions
 */
export const setContainerMenuWarningMessage = (message) => {
  dispatcher(types.CONTAINER_MENU_WARNING, { message });
  dispatcher(types.UPDATE_CONTAINER_MENU_VISIBILITY, { containerMenuOpen: true });
};

export const setContainerMenuVisibility = containerMenuOpen => dispatcher(
  types.UPDATE_CONTAINER_MENU_VISIBILITY,
  { containerMenuOpen },
);

export const setCloseEnvironmentMenus = () => dispatcher(
  types.CLOSE_ENVIRONMENT_MENUS,
  {},
);

export const toggleAdvancedVisible = advancedVisible => dispatcher(
  types.TOGGLE_ADVANCED_VISIBLE,
  { advancedVisible },
);
