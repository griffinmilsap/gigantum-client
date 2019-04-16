// vendor
import React, { Component } from 'react';
import uuidv4 from 'uuid/v4';
import classNames from 'classnames';
// assets
import './Prompt.scss';

let updateAvailable = false;

const Localhost = () => (
  <div>
    <p>Ensure Gigantum is running or restart the application</p>
    <p>
       If the problem continues to persist, follow the steps
      {' '}
      <a
        href="https://docs.gigantum.com/docs/client-interface-fails-to-load"
        rel="noopener noreferrer"
        target="_blank"
      >
          here
      </a>
       .
    </p>
  </div>
);

const Cloud = () => (
  <div>
    <p>Please ensure you have a valid internet connection.</p>
    <p>
       If the problem continues to persist, please report it&nbsp;
      {' '}
      <a
        href="https://spectrum.chat/gigantum"
        rel="noopener noreferrer"
        target="_blank"
      >
           here
      </a>
       .
    </p>
  </div>
);

const pingServer = () => {
  const apiHost = process.env.NODE_ENV === 'development' ? 'localhost:10000' : window.location.host;
  const uuid = uuidv4();
  const url = `${window.location.protocol}//${apiHost}${process.env.PING_API}?v=${uuid}`;
  const currentVersion = localStorage.getItem('currentVersion');

  return fetch(url, {
    method: 'GET',
  }).then((response) => {
    if (response.status === 200 && (response.headers.get('content-type') === 'application/json')) {
      if (!updateAvailable) {
        response.json().then((res) => {
          if (!currentVersion) {
            localStorage.setItem('currentVersion', res.revision);
          } else if (res.revision !== currentVersion) {
            updateAvailable = true;
            localStorage.setItem('currentVersion', res.revision);
          }
        });
      }
      return true;
    }
    return false;
  }).catch(error => false);
};

export default class Prompt extends Component {
  constructor(props) {
    super(props);

    this.state = {
      failureCount: 0,
      connected: false,
      promptState: true,
      updateAvailable: false,
    };
    this._handlePing = this._handlePing.bind(this);
  }

  componentDidMount() {
    this._handlePing();
    this.intervalId = setInterval(this._handlePing.bind(this), 2500);
  }

  /**
    @param {}
    pings server and checks when the api comes back up
  */
  _handlePing = () => {
    pingServer()
      .then((response) => {
        const { state } = this;
        if (updateAvailable !== state.updateAvailable) {
          this.setState({ updateAvailable });
        }
        if (response) {
          if (state.failureCount > 0) {
            window.location.reload();
          }

          this.setState({
            promptState: true,
            connected: true,
            failureCount: 0,
          });

          clearInterval(this.intervalId);

          this.intervalId = setInterval(this._handlePing.bind(this), 10000);
        } else {
          this.setState({
            failureCount: state.failureCount + 1,
            promptState: false,
          });

          clearInterval(this.intervalId);

          this.intervalId = setInterval(this._handlePing.bind(this), 2500);
        }
      });
  }


  render() {
    const { state } = this;
    // variables here
    const failedTwiceOrMore = (state.failureCount >= 2);
    const failedEightTimesOrMore = (state.failureCount >= 8);
    const lessThanEight = (state.failureCount < 8);
    // decalre css here
    const promptInfoCSS = classNames({
      Prompt__info: true,
      hidden: state.promptState,
    });
    const propmptLogoCSS = classNames({
      Prompt__logo: true,
      'Prompt__logo--final': failedEightTimesOrMore,
      'Prompt__logo--raised': failedTwiceOrMore && !failedEightTimesOrMore,
    });
    const loadingMessageCSS = classNames({
      'Prompt__loading-text': ((lessThanEight) && failedTwiceOrMore),
      hidden: !((failedTwiceOrMore) && lessThanEight),
    });
    const failureContainerCSS = classNames({
      'Prompt__failure-container': failedEightTimesOrMore,
      hidden: !failedEightTimesOrMore,
    });
    const updateAvailableCSS = classNames({
      Prompt__refresh: state.updateAvailable,
      hidden: !state.updateAvailable,
    });

    return (
      <div className="Prompt">
        <div className={promptInfoCSS}>
          <div className={propmptLogoCSS} />
          <div className={loadingMessageCSS}>
            Loading Please Wait...
          </div>
          <div className={failureContainerCSS}>
            <div className="Prompt__failure-text">
              <p>There was a problem loading Gigantum</p>
              {
                (window.location.hostname === 'localhost')
                  ? <Localhost />
                  : <Cloud />
              }
            </div>
          </div>
        </div>
        <div className={updateAvailableCSS}>
          <div>
            <p>A newer version of gigantum has been detected. Please refresh the page to view changes.</p>
          </div>
          <div>
            <button
              type="button"
              className="button--green"
              onClick={() => window.location.reload()}
            >
              Refresh
            </button>
          </div>
        </div>
      </div>
    );
  }
}
