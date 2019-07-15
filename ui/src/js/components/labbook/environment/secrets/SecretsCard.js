// vendor
import React, { Component } from 'react';
// components
import SecretsTable from './SecretsTable';
import AddSecret from './AddSecret';
// assets
import './SecretsCard.scss';

export default class PackageCard extends Component {
  state = {
  }

  render() {
    const { props } = this;
    return (
      <div className="SecretCard Card Card--auto Card--no-hover column-1-span-12 relative">
        <AddSecret
          secretsMutations={props.secretsMutations}
          relay={props.relay}
        />
        <SecretsTable
          secretsMutations={props.secretsMutations}
          secrets={props.secrets}
          relay={props.relay}
        />
      </div>
    );
  }
}
