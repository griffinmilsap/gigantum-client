/**
*   @param {array}
*   loops through activityRecords array and sorts into days
*   @return {Object}
*/
const transformActivity = (activityRecords, state) => {
  const activityTime = {};

  let count = 0;
  let previousTimeHash = null;
  let clusterIndex = 0;

  if (activityRecords) {
    activityRecords.edges.forEach((edge, index) => {
      if (edge && edge.node) {
        const date = (edge.node && edge.node.timestamp)
          ? new Date(edge.node.timestamp)
          : new Date();
        const year = date.getFullYear();
        const month = date.getMonth();
        const day = date.getDate();
        const timeHash = `${year}_${month}_${day}`;

        count = (edge.node.show || (previousTimeHash && (timeHash !== previousTimeHash)))
          ? 0
          : count + 1;

        if (count === 0) {
          clusterIndex = 0;
        }
        previousTimeHash = timeHash;

        const isExpandedHead = state && state.expandedClusterObject.has(index)
          && !state.expandedClusterObject.has(index - 1);
        const isExpandedEnd = state && state.expandedClusterObject.has(index)
          && !state.expandedClusterObject.has(index + 1);
        const isExpandedNode = state && state.expandedClusterObject.has(index);
        const attachedCluster = state && state.expandedClusterObject.has(index)
          && state.expandedClusterObject.get(index);
        const newActivityObject = {
          edge,
          date,
          collapsed: ((count > 2)
            && ((state && !state.expandedClusterObject.has(index))
            || (!state))),
          flatIndex: index,
          isExpandedHead,
          isExpandedEnd,
          isExpandedNode,
          attachedCluster,
        };

        if (count > 2 && ((state && !state.expandedClusterObject.has(index)) || (!state))) {
          if (count === 3) {
            const activityOne = activityTime[timeHash][activityTime[timeHash].length - 1];
            activityTime[timeHash][activityTime[timeHash].length - 1].collapsed = true;

            const activityTwo = activityTime[timeHash][activityTime[timeHash].length - 2];
            activityTime[timeHash][activityTime[timeHash].length - 2].collapsed = true;

            const clusterObject = {
              cluster: [activityTwo, activityOne, newActivityObject],
              attachedCluster,
              expanded: false,
              id: activityOne.edge.node.id,
            };

            activityTime[timeHash].pop();
            activityTime[timeHash].pop();

            if (activityTime[timeHash]) {
              activityTime[timeHash].push(clusterObject);
            } else {
              activityTime[timeHash] = [clusterObject];
            }

            clusterIndex = activityTime[timeHash].length - 1;
          } else {
            activityTime[timeHash][clusterIndex].cluster.push(newActivityObject);
          }
        } else {
          clusterIndex = 0;
          if (activityTime[timeHash]) {
            activityTime[timeHash].push(newActivityObject);
          } else {
            activityTime[timeHash] = [newActivityObject];
          }
        }
      }
    });
    return activityTime;
  }
  return [];
};


/**
*   @param {event} evt
*   assigns open-menu class to parent element and ActivityExtended to previous element
*   @return {}
*/
const toggleSubmenu = (evt) => {
  const submenu = evt.target.parentElement;
  const wrapper = submenu && submenu.parentElement;

  if (wrapper.previousSibling) {
    if (wrapper.previousSibling.className.indexOf('ActivityExtended') !== -1) {
      wrapper.previousSibling.classList.remove('ActivityExtended');
    } else {
      wrapper.previousSibling.classList.add('ActivityExtended');
    }
  } else if (wrapper.parentElement.previousSibling.className.indexOf('ActivityExtended') !== -1) {
    wrapper.parentElement.previousSibling.classList.remove('ActivityExtended');
  } else {
    wrapper.parentElement.previousSibling.classList.add('ActivityExtended');
  }

  if (submenu.className.indexOf('open-menu') !== -1) {
    submenu.classList.remove('open-menu');
  } else {
    submenu.classList.add('open-menu');
  }
};


export { transformActivity, toggleSubmenu };
