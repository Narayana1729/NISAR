import React from 'react';
import DomainWorkspace from '../../components/DomainWorkspace';
import { getDomainById } from '../../config/domains';

const domainConfig = getDomainById('domain5');

export default function Domain5Page() {
  return <DomainWorkspace domain={domainConfig} />;
}
