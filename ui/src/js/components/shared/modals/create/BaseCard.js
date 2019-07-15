// vendor
import React, { Component } from 'react';
import ReactMarkdown from 'react-markdown';
import classNames from 'classnames';
// assets
import './BaseCard.scss';


/**
* @param {Object}  node
*   @param {Array} node:languages
*   gets languages text
* return {string}
*/
const getLanguages = (node) => {
  let languages = node.languages.length > 1 ? 'Languages:' : 'Language:';
  node.languages.forEach((language, index) => languages += ` ${language}${index === node.languages.length - 1 ? '' : ','}`);

  return languages;
};

/**
* @param {Object}  node
*   @param {Array} node:developmentTools
*   gets languages text
* return {string}
*/
const getEnvironments = (node) => {
  let environments = node.developmentTools.length > 1 ? 'Environments:' : 'Environment:';
  node.developmentTools.forEach((environment, index) => environments += ` ${environment}${index === node.developmentTools.length - 1 ? '' : ','}`);

  return environments;
};

/**
* @param {Object}  node
*   @param {Array} node:installedPackages
*   gets languages text
* return {string}
*/
const getInstallDictionary = (node) => {
  const installedPackagesDictionary = {};
  node.installedPackages.forEach((val) => {
    const pkg = val.split('|');
    const pkgManager = pkg[0];
    const pkgName = pkg[1];
    const pkgVersion = pkg[2];
    installedPackagesDictionary[pkgManager] ? installedPackagesDictionary[pkgManager].push({ pkgName, pkgVersion }) : installedPackagesDictionary[pkgManager] = [{ pkgName, pkgVersion }];
  });

  return installedPackagesDictionary;
};

export default class BaseCard extends Component {
  state = {
    expanded: false,
  }

  /**
  * @param {} -
  * sets details view to expanded
  * return {}
  */
  _setBooleanState(evt, type) {
    const { state } = this;
    evt.preventDefault();
    evt.stopPropagation();

    this.setState({ [type]: !state[type] });
  }

  render() {
    const { props, state } = this;
    const { node } = props;

    const languages = getLanguages(node);
    const environments = getEnvironments(node);
    const installedPackagesDictionary = getInstallDictionary(node);

    const selectedBaseImage = classNames({
      BaseCard: true,
      'BaseCard--selected': (props.selectedBaseId === node.id),
      'BaseCard--expanded': state.expanded,
      Card: true,
    });
    const actionCSS = classNames({
      'BaseCard-actions': true,
      'BaseCard-actions--expanded': state.expanded,
    });

    return (
      <div
        onClick={() => props.selectBase(node)}
        className="BaseCard-wrapper"
      >
        <div className={selectedBaseImage}>
          <div className="BaseCard__icon">
            <img
              alt=""
              src={node.icon}
              height="50"
              width="50"
            />
          </div>

          <div className="BaseCard__details">
            <h6
              className="BaseCard__name"
              data-name={node.componentId}
            >
              {node.name}
            </h6>
            <p className="BaseCard__type">{`${node.osClass} ${node.osRelease}`}</p>
            <p className="BaseCard__languages">{languages}</p>
            <p className="BaseCard__environments">{environments}</p>
          </div>
          <div className="BaseCard__moreDetails">
            <p className="BaseCard__description">{node.description}</p>
            { (state.expanded)
            && (
            <div>
              <hr />
              <ReactMarkdown
                className="BaseCard__readme"
                source={node.readme}
              />
              { (Object.keys(installedPackagesDictionary).length !== 0)
                && (
                <table className="BaseDetails__table">
                  <thead>
                    <tr>
                      <th>Package Manager</th>
                      <th>Package Name</th>
                      <th>Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {
                        Object.keys(installedPackagesDictionary).map((manager, index) => installedPackagesDictionary[manager].map(pkg => (
                          <tr
                            key={manager + pkg.pkgName + pkg.pgkVersion}
                            className="BaseDetails__table-row"
                          >
                            <td>{manager}</td>
                            <td>{pkg.pkgName}</td>
                            <td>{pkg.pkgVersion}</td>
                          </tr>
                        )))
                      }
                  </tbody>
                </table>
                )
              }
            </div>
            )
          }
          </div>
          <div className={actionCSS}>
            <button
              onClick={(evt) => { this._setBooleanState(evt, 'expanded'); }}
              className="Btn Btn__dropdown Btn--flat"
            />
          </div>
        </div>
      </div>
    );
  }
}
