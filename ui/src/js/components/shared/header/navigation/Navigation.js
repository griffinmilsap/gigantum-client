// @flow
// vendor
import React, { PureComponent } from 'react';
import classNames from 'classnames';
import { Link } from 'react-router-dom';
// config
import Config from 'JS/config';
// assets
import './Navigation.scss';

/**
  @param {} -
  scrolls window to top
  @returns {}
*/
const scrollToTop = () => {
  window.scrollTo(0, 0);
};

type Props = {
  sectionType: string,
  match: Object,
  location: Object,
  owner: string,
}

class Navigation extends PureComponent<Props> {
  render() {
    const {
      sectionType,
      match,
      location,
      owner,
    } = this.props;
    const section = (sectionType === 'labbook') ? 'projects' : 'datasets';
    const name = (sectionType === 'labbook') ? match.params.labbookName : match.params.datasetName;

    return (
      <div className="Navigation flex-0-0-auto">

        <ul className="Tabs flex flex--row">
          {
          Config[`${sectionType}_navigation_items`].map((item) => {
            const pathArray = location.pathname.split('/');
            const selectedPath = (pathArray.length > 4) ? pathArray[pathArray.length - 1] : 'overview';
            // sets avtive nav item to overview if there is no menu item in the url
            const navItemCSS = classNames({
              Tab: true,
              'Tab--selected': (selectedPath === item.id),
            });

            return (
              <li
                id={item.id}
                key={item.id}
                className={navItemCSS}
                title={Config.navTitles[item.id]}
              >
                <Link
                  onClick={scrollToTop}
                  to={`../../../${section}/${owner}/${name}/${item.id}`}
                  replace
                >
                  {item.name}
                </Link>

              </li>
            );
          })
        }
        </ul>

      </div>
    );
  }
}

export default Navigation;
