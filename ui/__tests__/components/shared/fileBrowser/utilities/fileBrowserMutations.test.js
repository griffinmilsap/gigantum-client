// components
import FileBrowserMutations from 'Components/shared/fileBrowser/utilities/FileBrowserMutations';
// mutations
import DeleteLabbookFilesMutation from 'Mutations/fileBrowser/DeleteLabbookFilesMutation';
import MakeLabbookDirectoryMutation from 'Mutations/fileBrowser/MakeLabbookDirectoryMutation';
import MoveLabbookFileMutation from 'Mutations/fileBrowser/MoveLabbookFileMutation';
import DownloadDatasetFilesMutation from 'Mutations/fileBrowser/DownloadDatasetFilesMutation';
import CompleteBatchUploadTransactionMutation from 'Mutations/fileBrowser/CompleteBatchUploadTransactionMutation';


const mutationData = {
  owner: 'uitest',
  labbookName: 'ui-test-project',
  section: 'code',
  connection: 'CodeBrowser_allFiles',
  favoriteConnection: 'CodeFavorite_favorites',
  parentId: 'tempid',
};

jest.mock('Mutations/fileBrowser/DeleteLabbookFilesMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/MakeLabbookDirectoryMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/MoveLabbookFileMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/DownloadDatasetFilesMutation', () => jest.fn());
jest.mock('Mutations/fileBrowser/CompleteBatchUploadTransactionMutation', () => jest.fn());


describe('FileBrowserMutations', () => {
  let fileBrowserMutations = new FileBrowserMutations(mutationData);
  it('downloadDatasetFiles calls DownloadDatasetFilesMutation', () => {
      var data = {
        keys: ['file.py'],
        allKeys: ['file.py'],
        owner: 'uitest',
        datasetName: 'ui-test-dataset',
        labbookName: 'ui-test-project',
        labbookOwner: 'uitest',
      };

      fileBrowserMutations.downloadDatasetFiles(data, () => {});

      expect(DownloadDatasetFilesMutation.mock.calls.length).toEqual(1);
  });


  it('makeLabbookDirectory calls MakeLabbookDirectoryMutation', () => {
      var data = {
        key: 'file.py',
      };

      fileBrowserMutations.makeLabbookDirectory(data, () => {});

      expect(MakeLabbookDirectoryMutation.mock.calls.length).toEqual(1);
  });


  it('moveLabbookFile calls MoveLabbookFileMutation', () => {
      var data = {
        newKey: 'temp/file.py',
        edge: {
          node: {
            id: '',
            key: 'file.py',
            isDir: false,
          }
        },
        removeIds: 'tempid',
      };

      fileBrowserMutations.moveLabbookFile(data, () => {});

      expect(MoveLabbookFileMutation.mock.calls.length).toEqual(1);
  });

  it('deleteLabbookFiles calls DeleteLabbookFilesMutation', () => {
      var data = {
        filePaths: ['temp/file.py', 'file2/py'],
        edges: [{
          node: {
            id: '',
            key: 'temp/file.py',
            isDir: false,
            isFavorite: false,
          },
        },
        {
          node: {
            id: '',
            key: 'file2.py',
            isDir: false,
            isFavorite: true,
          },
        }],
      };

      fileBrowserMutations.deleteLabbookFiles(data, () => {});

      expect(DeleteLabbookFilesMutation.mock.calls.length).toEqual(1);
  });


  it('completeBatchUploadTransaction calls CompleteBatchUploadTransactionMutation', () => {
      var data = {
          transactionId: "tempId",
      };

      fileBrowserMutations.completeBatchUploadTransaction(data, () => {});

      expect(CompleteBatchUploadTransactionMutation.mock.calls.length).toEqual(1);
  });
})
