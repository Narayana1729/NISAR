import React from 'react';
import DomainWorkspace from '../../components/DomainWorkspace';
import { getDomainById } from '../../config/domains';

const domainConfig = getDomainById('domain3');

export default function Domain3Page() {
  return <DomainWorkspace domain={domainConfig} />;
}
