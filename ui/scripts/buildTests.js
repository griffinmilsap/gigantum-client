'use strict';
//#!/usr/bin/env babel-node --optional es7.asyncFunctions
import path from 'path'
import fs from 'fs'
import jsdom from 'jsdom-global'
import fetch from 'node-fetch'
import jest from 'jest'
import secret from './../config/secret'
import moveIdTokens from './tests/moveIdTokens';
const homedir = require('os').homedir();

import outputFileSync from 'output-file-sync'

const movePath = `${homedir}/gigantum/.labmanager/identity/cached_id_jwt`

jsdom()
// Do this as the first thing so that any code reading it knows the right env.]
global.test = function(){}
global.describe = function(){}
global.it = function(){}

process.env.BABEL_ENV = 'development';
process.env.NODE_ENV = 'development';

window.matchMedia = window.matchMedia || function() {
    return {
        matches : false,
        addListener : function() {},
        removeListener: function() {}
    };
};

moveIdTokens('./config/testData/cached_id_jwt', movePath, function(err){

  if(err === null){
    const createSnapshotTest = (testFile, route) => {

      let componentRelativePath = testFile.split('__tests__')[1]

      let componentImportPath = componentRelativePath.replace('.test.js', '').replace('/components', 'Components')

      let componentName = testFile.split('/')[testFile.split('/').length - 1].replace('.test.js', '')

      let relayData = require(__dirname + '/../' + route) //relay query

      const fileContent = `
      // vendor
      import React from 'react';
      import renderer from 'react-test-renderer';
      import {mount} from 'enzyme';
      import relayTestingUtils from 'relay-testing-utils';
      // components;
      import ${componentName} from '${componentImportPath}';

      test('Test ${componentName}', () => {
        const wrapper = renderer.create(<${componentName} />);

        const tree = wrapper.toJSON();

        expect(tree).toMatchSnapshot();
      });`;


          function ensureDirectoryExistence(filePath) {
              var dirname = path.dirname(filePath);
              if (fs.existsSync(dirname)) {
                return true;
              }
              ensureDirectoryExistence(dirname);
              fs.mkdirSync(dirname);
          }

          let filePath =  `${__dirname}/..${testFile.split('..')[1]}`;
          ensureDirectoryExistence(filePath)


          console.log(filePath)
          fs.exists(filePath, function(exists){
            console.log(exists)
            if(exists){
              //open existing file
              fs.open(filePath, 'w', (err, fd) => {

                if (err) throw err;



                //write to the file
                fs.write(fd, fileContent, 0, fileContent.length, null, function(err) {

                    if (err) throw 'error writing file: ' + err;

                    //close file
                    fs.close(fd, function() {
                        console.log(`${fd} updated`);
                    })
                });
              });
            }else{

              //create new files
              fs.writeFile(filePath, fileContent, { flag: 'wx' }, (err)=>{

                console.log(err)

              })
            }
          })

    };

    const variableReference = {
      labbookName: 'ui-test-project',
      datasetName: 'ui-test-dataset',
      name: 'ui-test-project',
      owner: 'cbutler',
      manager: 'pip',
      overviewSkip: false,
      activitySkip: false,
      skipPackages: false,
      environmentSkip: false,
      dataSkip: false,
      codeSkip: false,
      datasetSkip: false,
      inputSkip: false,
      outputSkip: false,
      labbookSkip: false,
      first: 20,
      cursor: null,
      hasNext: false,
      reverse: false,
      sort: 'desc',
      keys: [
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAxQYAAG8AAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAQgYAAG8AAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAkgQAAHgAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAtgUAAHgAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAA4gIAAHgAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAbgMAAIQAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAABgQAAHgAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAXAIAAHIAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAA1gEAAHIAAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAhwAAADsBAAA=',
        'log_50459b691a8075016c961c72eeb91661X19nX19sc24AAAAAAAAAAHMAAAA=',
      ],
      input: '',
      ids: [],
      path: '',
      key: '',
    }

    const buildQueryVariables = (route) => {
      const defs = require(__dirname + '/../' + route).operation.argumentDefinitions
      let variables = {}
      defs.forEach((def)=>{
          console.log(def)
         if(variableReference[def.name] !== undefined){
           let hasDataset = ((route.indexOf('dataset') > -1) || (route.indexOf('Dataset') > -1)) && (def.name === 'name');
           variables[def.name] = hasDataset ? variableReference.datasetName : variableReference[def.name]
         }else{
           console.log('missing variable' + def.name)
         }
      })

      return variables
    }


    const relayFilePostfixes = ["Query", "Pagination"]
    //reducer function
    const read = (dir) =>
      fs.readdirSync(dir)
        .reduce((files, file) => fs.statSync(path.join(dir, file)).isDirectory() ?
            files.concat(read(path.join(dir, file))) :
            files.concat(path.join(dir, file)),
          [])

    //reduce array to filepaths only
    const sourceJsFiles = read('src/js')


    //collect the relay genertated files
    let genteratedFiles = sourceJsFiles.filter((dirname) => {
      return((dirname.indexOf('__generated__') > -1) && (dirname.indexOf('_', (dirname.indexOf('__generated__') + 14)) < 0) && (dirname.indexOf('/mutations/') < 0))
    })

    /**
      Loop through generated files and check if a tests exists
    */
    let relayQueries = genteratedFiles.filter((route) => {
      let testFile = __dirname + '/../' + route.replace('src/js', '__tests__').replace('/__generated__/', '/').replace('.graphql.', '.test.').replace('Query', '').replace('Pagination', '')
      const exists = fs.existsSync(testFile)

      //if test does not exist create a snapshot test
      if (!exists){
        createSnapshotTest(testFile, route)
      }

      let isComponent = (route.indexOf('component') > -1)

      return isComponent
    }).map((route) => {
      //if tests exists create object for fetching data from the api
      // get the test file filepath
      let testFile = __dirname + '/../' + route.replace('src/js', '__tests__').replace('/__generated__/', '/').replace('.graphql.', '.test.')

      //remove relay post tags from file path
      relayFilePostfixes.forEach(function(postFix){
          if(testFile.indexOf(postFix) > -1){
            testFile = testFile.replace(postFix, '')
          }
      })

      //create variables using relay info and variableReference
      let variables = buildQueryVariables(route)
      return {
        dirname: route,
        relay: require(__dirname + '/../' + route), //relay query
        variables: variables, //import variables from test file
        testFile: testFile
      }
    })


    //loop through queries
    relayQueries.forEach((queryData) => {

      let variables = queryData.variables;
      //fetchData for test from the api
      fetch('http://localhost:10000/api/labbook/', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'authorization': `Bearer ${secret.accessToken}`,
          'Identity': secret.idToken
        },
        body: JSON.stringify({
          query: queryData.relay.params.text,
          variables: variables
        })
      }).then(function(response) {

          response.json().then(function(data){

              if(data.errors){
                console.log(`Error: ${data.errors[0].message}`)
              }
              //create a relayData file to output data
              let relayDataField = path.dirname(queryData.testFile) + '/__relaydata__/' + path.basename(queryData.testFile).replace('.test.js', '.json');

              //check if directories exist
              function ensureDirectoryExistence(filePath) {
                  var dirname = path.dirname(filePath);
                  if (fs.existsSync(dirname)) {
                    return true;
                  }
                  ensureDirectoryExistence(dirname);
                  fs.mkdirSync(dirname);
              }


              ensureDirectoryExistence(relayDataField)

              //if files exist overwrite data
              fs.exists(relayDataField, function(exists){

                if(exists){
                  //open existing file
                  fs.open(relayDataField, 'w', (err, fd) => {

                    if (err) throw err;

                    let stringData = JSON.stringify(data, null, ' ')

                    // write to the file
                    fs.write(
                      fd,
                      stringData,
                      0,
                      stringData.length,
                      function(err) {

                        if (err) throw 'error writing file: ' + err;

                        //close file
                        fs.close(fd, function() {
                            console.log(`${fd} updated`);
                        })
                    });
                  });
                } else {

                  // create new files
                  fs.writeFile(relayDataField, JSON.stringify(data), { flag: 'wx' }, (err)=>{
                    console.log(err)
                  })
                }
              })


          })
        }).catch(function(error) {
           console.log('request failed', error)
        })

    })
  } else {
    console.log(err)
  }
})
