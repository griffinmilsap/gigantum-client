module.exports = {
 "presets": [
   "@babel/preset-react",
   "@babel/preset-flow",
   ["@babel/preset-env", {
      "targets": {
          "esmodules": true
       }
    }
  ],
   "react-app"
 ],
 "plugins": [
   "relay",
   "@babel/plugin-syntax-dynamic-import",
   ["@gigantum/babel-plugin-selenium-id"],
   ["@babel/plugin-proposal-decorators", {
       "legacy": true,
   }],
   ["@babel/plugin-proposal-class-properties", { "loose" : true }],
   ["@babel/plugin-proposal-object-rest-spread", { "loose": true, "useBuiltIns": true }],
   [
     "module-resolver",
     {
       "root": [
         "./src",
         "./submodules"
       ],
       "alias": {
         "Mutations": "./src/js/mutations",
         "JS": "./src/js",
         "Components": "./src/js/components",
         "Submodules": "./submodules",
         "Images": './src/images'
       }
     }
   ]
 ],
 "env": {
  "test": {
    "presets": [
      ["@babel/preset-env", {
         "targets": {
             "esmodules": true
          }
       }
     ],
      '@babel/preset-react',
    ],
    "plugins": [
      '@babel/plugin-transform-modules-commonjs',
      'babel-plugin-dynamic-import-node-babel-7',
      ["@babel/plugin-proposal-decorators", {
        "legacy": true,
      }],
      ["@babel/plugin-proposal-class-properties", { "loose" : true }],
      ["@gigantum/babel-plugin-selenium-id"],
    ],
  },
},
}
