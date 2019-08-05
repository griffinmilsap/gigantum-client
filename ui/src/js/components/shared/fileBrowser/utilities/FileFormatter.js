export default class FileFormatter {
  constructor(worker) {
    const code = worker.toString();
    const blob = new Blob([`(${code})()`]);
    return new Worker(URL.createObjectURL(blob));
  }
}
/**
*  @param {}
*  Worker that handles the formating and grouping of files
*  @return {}
*/
export const fileHandler = () => {
  /* eslint-disable */
    self.addEventListener('message', (evt) => {
        let edges = evt.data.files;
        let edgesToSort = JSON.parse(JSON.stringify(edges));
        let fileObject = {};
        const { search, linkedDatasets } = evt.data;
        const searchLowerCase = search.toLowerCase();

       const sortEdges =  (edges, datasetName, datasetOwner) => {
        if (search !== '') {
          let edgesSearchMatch = edges.filter((edge) => {
            const lowerCaseKey = edge.node.key.toLowerCase();
            return (lowerCaseKey.indexOf(searchLowerCase) > -1);
          });

          edges = edges.filter((edge) => {
            let keyMatch = false;
            edgesSearchMatch.forEach((matchEdge) => {
              if (matchEdge.node.key.indexOf(edge.node.key) > -1) {
                keyMatch = true;
              }
            });
            return keyMatch;
          });
        }

       if (datasetName && (edges.length === 0) && (datasetName.toLowerCase().indexOf(searchLowerCase) > -1)) {
          fileObject[datasetName] = {
            children: {
            },
            edge: {
              node: {
                key: `${datasetName}/`,
                isDir: true,
                isDataset: !!datasetName,
                modifiedAt: Math.floor(Date.now() / 1000),
                owner: datasetOwner || null,
                datasetName: datasetName || null,
               },
            },
            index: 0,
          };
        }
        edges.forEach((edge, index) => {

          if (edge.node) {
            let key = edge.node.key.toLowerCase();
            let searchLowerCase = search.toLowerCase();
            let currentObject = fileObject;
            const keyToSplit = datasetName ? `${datasetName}/${edge.node.key}` : edge.node.key;
            let splitKey = keyToSplit.split('/').filter(key => key.length);

            splitKey.forEach((key, index) => {
                if (currentObject && (index === (splitKey.length - 1))) {
                    if (!currentObject[key]) {
                      currentObject[key] = {
                        edge,
                        index,
                      };
                      if (datasetName) {
                        currentObject[key].edge.node.key = `${datasetName}/${currentObject[key].edge.node.key}`
                        currentObject[key].edge.node.owner = datasetOwner
                        currentObject[key].edge.node.datasetName = datasetName
                      }
                    } else if(!currentObject[key].edge || !currentObject[key].edge.node || !currentObject[key].edge.node.isDataset) {
                      currentObject[key].edge = edge;
                      if (datasetName) {
                        currentObject[key].edge.node.key = `${datasetName}/${currentObject[key].edge.node.key}`
                        currentObject[key].edge.node.owner = datasetOwner
                        currentObject[key].edge.node.datasetName = datasetName
                      }
                    }
                } else if (currentObject && !currentObject[key]) {
                    const newKey = `${splitKey.slice(0, index + 1).join('/')}/`;
                    currentObject[key] = {
                      children: {},
                      edge: {
                        node: {
                          key: newKey,
                          isDir: true,
                          isLocal: true,
                          isDataset: !!datasetName,
                          modifiedAt: Math.floor(Date.now() / 1000),
                          owner: datasetOwner || null,
                          datasetName: datasetName || null,
                         },
                      },
                      index,
                    };
                    currentObject = currentObject[key].children;
                } else if (currentObject && currentObject[key] && !currentObject[key].children) {
                    currentObject[key].children = {};
                    currentObject = currentObject[key].children;
                } else {
                  currentObject = currentObject[key].children;
                }
              });
            }
          });
        }
        if (linkedDatasets) {
          linkedDatasets.forEach(dataset => {
            sortEdges(dataset.allFiles.edges, dataset.name, dataset.owner)
          })

        }
        sortEdges(edgesToSort)

        const hash = btoa(unescape(encodeURIComponent(JSON.stringify(fileObject) + search)));
        postMessage({ files: fileObject, hash });
    });
};

    /* eslint-enable */
