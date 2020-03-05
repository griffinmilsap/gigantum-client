// vendor
import React from 'react';
import classNames from 'classnames';
// components
import Description from './description/Description';
// assets
import './TitleSection.scss';

const TitleSection = (props) => {
  const {
    sectionType,
  } = props;
  const section = props[sectionType];
  const {
    visibility,
  } = section;
  const title = `${section.owner} / ${section.name}`;
  // declare css here
  const visibilityIconCSS = classNames({
    [`TitleSection__${visibility}`]: true,
    [`TitleSection__${visibility}--sticky`]: props.isSticky,
    'Tooltip-data Tooltip-data--small': true,
  });

  return (
    <div className="TitleSection">

      <div className="TitleSection__namespace">
        <div className="TitleSection__namespace-title">{title}</div>
        { ((visibility === 'private') || (visibility === 'public'))
            && (
            <div
              className={visibilityIconCSS}
              data-tooltip={visibility}
            />
            )
        }
      </div>

      {
        !props.isSticky && <Description {...props} />
      }
    </div>
  );
}

export default TitleSection;
