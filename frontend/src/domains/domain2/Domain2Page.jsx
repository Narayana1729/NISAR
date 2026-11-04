import React from 'react';
import DomainWorkspace from '../../components/DomainWorkspace';
import { getDomainById } from '../../config/domains';

const domainConfig = getDomainById('domain2');

export default function Domain2Page() {
  return <DomainWorkspace domain={domainConfig} />;
}
