/**
  @param {Object} node
  flattens node values into a string to make it searchable
*/
const flattenCombineNodeValues = ((node) => {
  let lowercaseJSON = '';
  Object.keys(node).forEach((key) => {
    if (typeof node[key] === 'string' && key !== 'icon') {
      lowercaseJSON += `${node[key].toLowerCase()} /n`;
    }
  });
  return lowercaseJSON;
});

/**
  @param {Object} node
  @param {Array} tags
  @param {String} lowercaseJSON
  @param {Boolean} isReturned
  searches node for tags and returns true is there is a match;
*/
const searchTagsForMatch = ((node, tags, lowercaseJSON, isReturned) => {
  tags.forEach(({ text, className }) => {
    if (className === 'Languages') {
      if (node.languages.indexOf(text) === -1) {
        isReturned = false;
      }
    } else if (className === 'Development Environments') {
      if (node.developmentTools.indexOf(text) === -1) {
        isReturned = false;
      }
    } else if (className === 'Tags') {
      if (node.tags.indexOf(text) === -1) {
        isReturned = false;
      }
    } else if (className === 'CUDA Version') {
      if (node.cudaVersion !== text) {
        isReturned = false;
      }
    } else if (lowercaseJSON.indexOf(text.toLowerCase()) === -1) {
      isReturned = false;
    }
  });

  return isReturned;
});


/**
  @param {object} projectBases
  determines filter criteria for project types
  @return {object} filters
*/
const createProjectFilters = (projectBases) => {
  const filters = {
    Languages: [],
    'Development Environments': [],
    Tags: [],
  };
  const tags = new Set();
  const languages = new Set();
  const devTools = new Set();
  const cudaVersions = new Set();

  projectBases.forEach(({ node }) => {
    node.tags.forEach((tag) => {
      if (!tags.has(tag)) {
        tags.add(tag);
      }
      node.languages.forEach((language) => {
        if (!languages.has(language)) {
          languages.add(language);
        }
      });
      node.developmentTools.forEach((devTool) => {
        if (!devTools.has(devTool)) {
          devTools.add(devTool);
        }
      });
      if (!cudaVersions.has(node.cudaVersion) && node.cudaVersion) {
        cudaVersions.add(node.cudaVersion);
      }
    });
  });
  filters.Tags = Array.from(tags);
  filters.Languages = Array.from(languages);
  filters['Development Environments'] = Array.from(devTools);
  filters['CUDA Version'] = Array.from(cudaVersions).sort((a, b) => Number(b) - Number(a));

  return filters;
};


/**
  @param {Array} projects
  filters projects based on selected filters
*/
const filterProjects = (projects, tags) => {
  const mostRecent = localStorage.getItem('latest_base');
  let mostRecentNode;

  // loop through projects for filter
  const filteredProjects = projects.filter(({ node }) => {
    const lowercaseJSON = flattenCombineNodeValues(node);
    let isReturned = true;
    // set most recent if matches localStorage
    if (mostRecent === node.componentId) {
      isReturned = false;
      mostRecentNode = node;
    }
    if (!mostRecent && node.componentId === 'python3-data-science') {
      isReturned = false;
      mostRecentNode = node;
    }
    // check if tags match base image
    isReturned = searchTagsForMatch(node, tags, lowercaseJSON, isReturned);
    return isReturned;
  });

  // search most recent, move to the top if matches search query
  if (mostRecentNode) {
    let isMostRecentReturned = true;
    const lowercaseJSON = flattenCombineNodeValues(mostRecentNode);

    // check if tags match base image
    isMostRecentReturned = searchTagsForMatch(mostRecentNode, tags, lowercaseJSON, isMostRecentReturned);

    if (isMostRecentReturned) {
      filteredProjects.unshift({ node: mostRecentNode });
    }
  }
  return filteredProjects;
};


/**
  @param {Array} datasets
  filters datasets based on selected filters
*/
const filterDatasets = (datasets, stateTags) => {
  const tags = stateTags.map(tagObject => tagObject.text.toLowerCase());
  return datasets.filter((dataset) => {
    const lowercaseReadme = dataset.readme.toLowerCase();
    const lowercaseDescription = dataset.description.toLowerCase();
    const lowercaseName = dataset.name.toLowerCase();
    let isReturned = true;
    if ((tags.indexOf('Managed') > -1) && !dataset.isManaged
        || (tags.indexOf('Unmanaged') > -1) && dataset.isManaged) {
      isReturned = false;
    }

    tags.forEach((tag) => {
      if (tag !== 'Managed' && tag !== 'Unmanaged'
          && dataset.tags.indexOf(tag) === -1
          && lowercaseReadme.indexOf(tag) === -1
          && lowercaseDescription.indexOf(tag) === -1
          && lowercaseName.indexOf(tag) === -1) {
        isReturned = false;
      }
    });
    return isReturned;
  });
};

/**
  @param {object} datasetBases
  determines filter criteria for dataset types
  @return {object} filters
*/
const createDatasetFilters = (datasetBases) => {
  const filters = {
    'Dataset Type': ['Managed', 'Unmanaged'],
    Tags: [],
  };
  const tags = new Set();
  datasetBases.forEach((datasetBase) => {
    datasetBase.tags.forEach((tag) => {
      if (!tags.has(tag)) {
        tags.add(tag);
      }
    });
  });
  filters.Tags = Array.from(tags);
  return filters;
};

const SelectBaseUtils = {
  flattenCombineNodeValues,
  searchTagsForMatch,
  createProjectFilters,
  filterProjects,
  createDatasetFilters,
  filterDatasets,
};


export default SelectBaseUtils;

export {
  flattenCombineNodeValues,
  searchTagsForMatch,
  createProjectFilters,
  filterProjects,
  createDatasetFilters,
  filterDatasets,
};
